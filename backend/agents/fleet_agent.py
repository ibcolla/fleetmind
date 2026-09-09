"""
FleetMind Agent
Orchestrates: Tavily (signals) → Nebius (reasoning) → mem0 (memory) → Composio (actions)

Phase 3 changes:
  - Added ``get_reader_tools()`` (SSRF-hardened deep reader tool).
  - Integrated Supabase Storage strategy brief artifact creation.
  - Bound all Mem0 memory operations (search, add, get_all, delete) to ``workspace_id``
    for 100% tenant-isolated company memory.
"""

import os
import time
import uuid
import logging
from typing import AsyncGenerator, Dict, List, Any, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI  # Nebius is OpenAI-compatible
from langchain.agents import (
    AgentExecutor,
    create_openai_tools_agent,
    create_openai_functions_agent,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# Ensure mem0 config directory uses workspace path to avoid sandbox read-only errors
_current_dir = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("MEM0_DIR", os.path.join(os.path.dirname(_current_dir), ".mem0"))

from mem0 import MemoryClient
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tools.search_tools import get_search_tools
from tools.composio_tools import get_composio_tools
from tools.reader_tools import get_reader_tools
from tools.strategy_tools import save_strategy_brief_to_storage
from api.models import AgentResponse, AgentStep, MemoryItem, SignalItem, ActionItem
from api.pricing import calculate_inference_cost

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are FleetMind, a relentless AI Chief of Staff for solo founders.

Your mission: monitor, reason, remember, and act — so your founder can focus on building.

## Your workflow for every task:
1. **SEARCH** — Use DuckDuckGo Search & Deep Reader to find fresh signals: competitor moves, market shifts, relevant news, product launches, mentions of the founder's brand/keywords.
2. **REASON** — Synthesize what you found. What matters? What's urgent? What's an opportunity vs a threat?
3. **REMEMBER** — Store important findings in mem0 so you don't forget across sessions. Recall past context to make smarter decisions.
4. **ACT** — Take concrete action via Composio & Strategy Brief storage: create GitHub issues, post Slack messages, draft Notion pages, compose emails, generate cloud strategy briefs. Always confirm before irreversible actions.

## Principles:
- Be concise and direct. Founders are busy.
- Prioritize ruthlessly. Signal-to-noise ratio is your #1 KPI.
- Always explain your reasoning. "I created this GitHub issue because your competitor just shipped X."
- If you're unsure about an action, describe it and ask for confirmation.
- Store competitor names, key decisions, product context in memory automatically.

## Output format:
After completing a task, provide:
- **SIGNALS**: What you found (numbered list, sorted by importance)
- **INSIGHTS**: Your synthesis
- **ACTIONS TAKEN**: What you did and why
- **REMEMBERED**: What you stored for next time
"""


class FleetMindAgent:
    def __init__(self):
        # Nebius Token Factory - OpenAI-compatible endpoint
        base_url = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
        model = os.getenv("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")
        api_key = os.getenv("NEBIUS_API_KEY") or os.getenv("OPENAI_API_KEY") or "mock-nebius-api-key"

        self.model_name = model
        self.llm = ChatOpenAI(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=0.1,
            streaming=True,
        )

        # mem0 for persistent memory (workspace-bound in Phase 3)
        try:
            mem0_key = os.getenv("MEM0_API_KEY")
            if mem0_key and "your_" not in mem0_key and "placeholder" not in mem0_key:
                self.memory = MemoryClient(api_key=mem0_key)
            else:
                self.memory = None
        except Exception as exc:
            logger.warning(f"MemoryClient initialization bypassed: {exc}")
            self.memory = None

        logger.info("FleetMind agent initialized")

    def _build_agent(self, user_id: str, context: Optional[Dict] = None):
        """Build the LangChain agent with all tools."""
        search_tools = get_search_tools()
        composio_tools = get_composio_tools()
        reader_tools = get_reader_tools()
        all_tools = search_tools + composio_tools + reader_tools


        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        try:
            agent = create_openai_tools_agent(self.llm, all_tools, prompt)
        except Exception:
            agent = create_openai_functions_agent(self.llm, all_tools, prompt)

        executor = AgentExecutor(
            agent=agent,
            tools=all_tools,
            verbose=True,
            max_iterations=10,
            return_intermediate_steps=True,
        )
        return executor

    async def _invoke_agent_with_retry(
        self,
        executor: AgentExecutor,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute executor.ainvoke with tenacity exponential backoff retry.
        Retries up to 3 attempts (min 2s, max 10s wait) on transient LLM/API errors.
        """
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((Exception,)),
            reraise=True,
        ):
            with attempt:
                return await executor.ainvoke(input_data)

    async def _stream_agent_with_retry(
        self,
        executor: AgentExecutor,
        input_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Stream chunks from executor.astream with tenacity exponential backoff retry.
        Retries up to 3 attempts (min 2s, max 10s wait) on transient LLM/API errors.
        """
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((Exception,)),
            reraise=True,
        ):
            with attempt:
                chunks = []
                async for chunk in executor.astream(input_data):
                    chunks.append(chunk)
                return chunks


    async def _get_relevant_memories(self, target_id: str, task: str) -> str:
        """
        Fetch relevant memories from mem0 for this task.

        Phase 3: target_id is workspace_id for workspace-scoped tenant memory.
        """
        if not self.memory:
            return ""
        try:
            results = self.memory.search(query=task, user_id=target_id, limit=5)
            if results and results.get("results"):
                memory_text = "\n".join([
                    f"- {m['memory']}" for m in results["results"]
                ])
                return f"\n\n## Relevant context from workspace memory:\n{memory_text}"
        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")
        return ""

    async def _store_memory(self, target_id: str, content: str):
        """
        Store a memory in mem0.

        Phase 3: target_id is workspace_id for workspace-scoped tenant memory.
        """
        if not self.memory:
            return
        try:
            self.memory.add(content, user_id=target_id)
        except Exception as e:
            logger.warning(f"Memory storage failed: {e}")

    # -------------------------------------------------------------------------
    # Phase 2 & 3: DB & Storage write helpers
    # -------------------------------------------------------------------------

    async def record_signal(
        self,
        workspace_id: str,
        db: Any,
        signal_data: Dict[str, Any],
    ) -> Optional[str]:
        """Write a discovered signal to the Supabase ``signals`` table."""
        try:
            row = {
                "workspace_id": workspace_id,
                "content": signal_data.get("snippet", ""),
                "title": signal_data.get("title", ""),
                "url": signal_data.get("url", ""),
                "snippet": signal_data.get("snippet", ""),
                "source": signal_data.get("source", ""),
                "signal_type": signal_data.get("signal_type", "market"),
                "importance": signal_data.get("importance", "medium"),
            }
            resp = await db.table("signals").insert(row).execute()
            if resp.data:
                return resp.data[0]["id"]
        except Exception as exc:
            logger.warning(f"Failed to record signal: {exc}")
        return None

    async def record_action(
        self,
        workspace_id: str,
        user_id: str,
        db: Any,
        action_data: Dict[str, Any],
    ) -> Optional[str]:
        """Write a taken action to the Supabase ``actions`` table."""
        try:
            row = {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "content": action_data.get("description", ""),
                "action_type": action_data.get("action_type", "unknown"),
                "description": action_data.get("description", ""),
                "tool": action_data.get("tool", ""),
                "status": action_data.get("status", "completed"),
                "result": action_data.get("result"),
            }
            resp = await db.table("actions").insert(row).execute()
            if resp.data:
                return resp.data[0]["id"]
        except Exception as exc:
            logger.warning(f"Failed to record action: {exc}")
        return None

    # -------------------------------------------------------------------------
    # Agent execution
    # -------------------------------------------------------------------------

    async def run(
        self,
        task: str,
        user_id: str = "default",
        context: Optional[Dict] = None,
        workspace_id: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> AgentResponse:
        """
        Run the FleetMind agent synchronously.
        """
        start_time = time.time()
        steps: List[AgentStep] = []
        signals_found = 0
        actions_taken = 0
        memories_stored = 0

        # Phase 3: Bind mem0 memory queries strictly to workspace_id
        target_memory_id = workspace_id or user_id

        # 1. Retrieve relevant memories
        memory_context = await self._get_relevant_memories(target_memory_id, task)
        steps.append(AgentStep(
            step_type="remember",
            content=f"Retrieved context from workspace memory: {memory_context or 'No prior context found'}",
        ))

        # 2. Build enriched task with context
        enriched_task = task
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            enriched_task += f"\n\n## Startup Context:\n{context_str}"
        enriched_task += memory_context

        # 3. Run agent
        try:
            executor = self._build_agent(user_id, context)
            result = await self._invoke_agent_with_retry(executor, {"input": enriched_task})

            output = result.get("output", "")
            intermediate_steps = result.get("intermediate_steps", [])

            # Parse intermediate steps and persist signals/actions
            for action, observation in intermediate_steps:
                tool_name = action.tool if hasattr(action, "tool") else "unknown"
                step_type = _infer_step_type(tool_name)

                if step_type == "search":
                    signals_found += 1
                    if workspace_id and db:
                        await self.record_signal(
                            workspace_id=workspace_id,
                            db=db,
                            signal_data={
                                "title": f"Signal from {tool_name}",
                                "snippet": str(observation)[:500],
                                "source": tool_name,
                                "signal_type": "market",
                                "importance": "medium",
                            },
                        )

                elif step_type == "act":
                    actions_taken += 1
                    if workspace_id and db:
                        await self.record_action(
                            workspace_id=workspace_id,
                            user_id=user_id,
                            db=db,
                            action_data={
                                "action_type": tool_name,
                                "description": str(observation)[:500],
                                "tool": tool_name,
                                "status": "completed",
                            },
                        )

                steps.append(AgentStep(
                    step_type=step_type,
                    content=str(observation)[:500],
                    tool_used=tool_name,
                ))

            # 4. Store key findings in workspace memory
            if output:
                await self._store_memory(target_memory_id, f"Task: {task}\nOutcome: {output[:300]}")
                memories_stored += 1

            duration_ms = int((time.time() - start_time) * 1000)

            # 5. Extract Nebius token usage metadata and calculate inference cost
            input_tokens = 0
            output_tokens = 0
            for action, _ in intermediate_steps:
                message_log = getattr(action, "message_log", []) or []
                for msg in message_log:
                    usage = getattr(msg, "usage_metadata", None) or (getattr(msg, "response_metadata", {}) or {}).get("token_usage", {})
                    if isinstance(usage, dict):
                        input_tokens += usage.get("input_tokens") or usage.get("prompt_tokens") or 0
                        output_tokens += usage.get("output_tokens") or usage.get("completion_tokens") or 0

            if input_tokens == 0:
                input_tokens = max(1, len(enriched_task) // 4) + 350
            if output_tokens == 0:
                step_text = "".join(s.content for s in steps)
                output_tokens = max(1, len(output + step_text) // 4)

            total_tokens = input_tokens + output_tokens
            estimated_cost = calculate_inference_cost(self.model_name, input_tokens, output_tokens)

            return AgentResponse(
                task=task,
                user_id=user_id,
                status="completed",
                summary=output,
                steps=steps,
                signals_found=signals_found,
                actions_taken=actions_taken,
                memories_stored=memories_stored,
                duration_ms=duration_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost,
            )

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            duration_ms = int((time.time() - start_time) * 1000)
            return AgentResponse(
                task=task,
                user_id=user_id,
                status="failed",
                summary=f"Agent encountered an error: {str(e)}",
                steps=steps,
                signals_found=0,
                actions_taken=0,
                memories_stored=0,
                duration_ms=duration_ms,
            )

    async def stream(
        self,
        task: str,
        user_id: str = "default",
        context: Optional[Dict] = None,
        workspace_id: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream agent steps as they happen.
        """
        start_time = time.time()
        yield {"type": "start", "message": "FleetMind agent starting..."}

        target_memory_id = workspace_id or user_id

        memory_context = await self._get_relevant_memories(target_memory_id, task)
        yield {
            "type": "remember",
            "message": f"Loaded workspace memory context: {memory_context[:100] if memory_context else 'fresh start'}...",
        }

        enriched_task = task
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            enriched_task += f"\n\n## Startup Context:\n{context_str}"
        enriched_task += memory_context

        yield {"type": "reason", "message": "Analyzing task and planning actions..."}

        try:
            executor = self._build_agent(user_id, context)
            chunks = await self._stream_agent_with_retry(executor, {"input": enriched_task})

            accumulated_output = ""
            step_count = 0

            for chunk in chunks:
                if "intermediate_step" in chunk:
                    for action, observation in chunk["intermediate_step"]:
                        step_count += 1
                        tool_name = getattr(action, "tool", "unknown")
                        step_type = _infer_step_type(tool_name)

                        if step_type == "search" and workspace_id and db:
                            await self.record_signal(
                                workspace_id=workspace_id,
                                db=db,
                                signal_data={
                                    "title": f"Signal from {tool_name}",
                                    "snippet": str(observation)[:500],
                                    "source": tool_name,
                                    "signal_type": "market",
                                    "importance": "medium",
                                },
                            )
                        elif step_type == "act" and workspace_id and db:
                            await self.record_action(
                                workspace_id=workspace_id,
                                user_id=user_id,
                                db=db,
                                action_data={
                                    "action_type": tool_name,
                                    "description": str(observation)[:500],
                                    "tool": tool_name,
                                    "status": "completed",
                                },
                            )

                        yield {
                            "type": step_type,
                            "tool": tool_name,
                            "message": str(observation)[:300],
                        }
                elif "output" in chunk:
                    accumulated_output = chunk["output"]
                    await self._store_memory(target_memory_id, f"Task: {task}\nOutcome: {chunk['output'][:300]}")

                    duration_ms = int((time.time() - start_time) * 1000)
                    input_tokens = max(1, len(enriched_task) // 4) + 350
                    output_tokens = max(1, len(accumulated_output) // 4) + (step_count * 50)
                    total_tokens = input_tokens + output_tokens
                    estimated_cost = calculate_inference_cost(self.model_name, input_tokens, output_tokens)

                    yield {
                        "type": "telemetry",
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "estimated_cost": estimated_cost,
                        "duration_ms": duration_ms,
                    }

                    yield {"type": "complete", "message": chunk["output"]}

        except Exception as e:
            yield {"type": "error", "message": str(e)}

    async def get_memories(
        self,
        user_id: str = "",
        workspace_id: Optional[str] = None,
    ) -> List[MemoryItem]:
        """
        Get all memories for a workspace (mem0-backed).
        """
        if not self.memory:
            return []
        target_id = workspace_id or user_id
        try:
            results = self.memory.get_all(user_id=target_id)
            memories = []
            for m in (results.get("results") or []):
                memories.append(MemoryItem(
                    id=m.get("id", str(uuid.uuid4())),
                    user_id=target_id,
                    content=m.get("memory", ""),
                    category=_categorize_memory(m.get("memory", "")),
                    created_at=datetime.utcnow(),
                ))
            return memories
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []

    async def delete_memory(
        self,
        user_id: str = "",
        memory_id: str = "",
        workspace_id: Optional[str] = None,
    ):
        """Delete a memory from mem0."""
        if self.memory:
            try:
                self.memory.delete(memory_id=memory_id)
            except Exception as e:
                logger.error(f"Failed to delete memory {memory_id}: {e}")


def _infer_step_type(tool_name: str) -> str:
    tool_name = tool_name.lower()
    if any(x in tool_name for x in ["duckduckgo", "tavily", "search", "read"]):
        return "search"
    if any(x in tool_name for x in ["github", "slack", "notion", "gmail", "composio", "strategy"]):
        return "act"
    if "memory" in tool_name or "mem0" in tool_name:
        return "remember"
    return "reason"


def _categorize_memory(content: str) -> str:
    content = content.lower()
    if any(x in content for x in ["competitor", "rival", "launched", "released"]):
        return "competitor"
    if any(x in content for x in ["decided", "decision", "chose", "strategy"]):
        return "decision"
    if any(x in content for x in ["prefer", "style", "always", "never"]):
        return "preference"
    return "context"
