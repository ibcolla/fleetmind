"""
FleetMind Agent
Orchestrates: Tavily (signals) → Nebius (reasoning) → mem0 (memory) → Composio (actions)
"""

import os
import time
import uuid
import logging
from typing import AsyncGenerator, Dict, List, Any, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI  # Nebius is OpenAI-compatible
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from mem0 import MemoryClient

from tools.tavily_tools import get_tavily_tools
from tools.composio_tools import get_composio_tools
from api.models import AgentResponse, AgentStep, MemoryItem, SignalItem, ActionItem

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are FleetMind, a relentless AI Chief of Staff for solo founders.

Your mission: monitor, reason, remember, and act — so your founder can focus on building.

## Your workflow for every task:
1. **SEARCH** — Use Tavily to find fresh signals: competitor moves, market shifts, relevant news, product launches, mentions of the founder's brand/keywords.
2. **REASON** — Synthesize what you found. What matters? What's urgent? What's an opportunity vs a threat?
3. **REMEMBER** — Store important findings in mem0 so you don't forget across sessions. Recall past context to make smarter decisions.
4. **ACT** — Take concrete action via Composio: create GitHub issues, post Slack messages, draft Notion pages, compose emails. Always confirm before irreversible actions.

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
        # Nebius AI - OpenAI-compatible endpoint
        self.llm = ChatOpenAI(
            base_url="https://api.studio.nebius.com/v1/",
            api_key=os.getenv("NEBIUS_API_KEY"),
            model=os.getenv("NEBIUS_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct"),
            temperature=0.1,
            streaming=True,
        )

        # mem0 for persistent memory
        self.memory = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

        # In-memory store for signals & actions (replace with DB in prod)
        self._signals_store: Dict[str, List[Dict]] = {}
        self._actions_store: Dict[str, List[Dict]] = {}

        logger.info("FleetMind agent initialized")

    def _build_agent(self, user_id: str, context: Optional[Dict] = None):
        """Build the LangChain agent with all tools."""
        tavily_tools = get_tavily_tools()
        composio_tools = get_composio_tools()
        all_tools = tavily_tools + composio_tools

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_functions_agent(self.llm, all_tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=all_tools,
            verbose=True,
            max_iterations=10,
            return_intermediate_steps=True,
        )
        return executor

    async def _get_relevant_memories(self, user_id: str, task: str) -> str:
        """Fetch relevant memories from mem0 for this task."""
        try:
            results = self.memory.search(query=task, user_id=user_id, limit=5)
            if results and results.get("results"):
                memory_text = "\n".join([
                    f"- {m['memory']}" for m in results["results"]
                ])
                return f"\n\n## Relevant context from memory:\n{memory_text}"
        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")
        return ""

    async def _store_memory(self, user_id: str, content: str):
        """Store a memory in mem0."""
        try:
            self.memory.add(content, user_id=user_id)
        except Exception as e:
            logger.warning(f"Memory storage failed: {e}")

    async def run(
        self,
        task: str,
        user_id: str = "default",
        context: Optional[Dict] = None,
    ) -> AgentResponse:
        """Run the FleetMind agent synchronously."""
        start_time = time.time()
        steps: List[AgentStep] = []
        signals_found = 0
        actions_taken = 0
        memories_stored = 0

        # 1. Retrieve relevant memories
        memory_context = await self._get_relevant_memories(user_id, task)
        steps.append(AgentStep(
            step_type="remember",
            content=f"Retrieved context from memory: {memory_context or 'No prior context found'}",
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
            result = await executor.ainvoke({"input": enriched_task})

            output = result.get("output", "")
            intermediate_steps = result.get("intermediate_steps", [])

            # Parse intermediate steps
            for action, observation in intermediate_steps:
                tool_name = action.tool if hasattr(action, "tool") else "unknown"
                step_type = _infer_step_type(tool_name)

                if step_type == "search":
                    signals_found += 1
                elif step_type == "act":
                    actions_taken += 1

                steps.append(AgentStep(
                    step_type=step_type,
                    content=str(observation)[:500],
                    tool_used=tool_name,
                ))

            # 4. Store key findings in memory
            if output:
                await self._store_memory(user_id, f"Task: {task}\nOutcome: {output[:300]}")
                memories_stored += 1

            duration_ms = int((time.time() - start_time) * 1000)

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
    ) -> AsyncGenerator[Dict, None]:
        """Stream agent steps as they happen."""
        yield {"type": "start", "message": "FleetMind agent starting..."}

        memory_context = await self._get_relevant_memories(user_id, task)
        yield {
            "type": "remember",
            "message": f"Loaded memory context: {memory_context[:100] if memory_context else 'fresh start'}...",
        }

        enriched_task = task
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            enriched_task += f"\n\n## Startup Context:\n{context_str}"
        enriched_task += memory_context

        yield {"type": "reason", "message": "Analyzing task and planning actions..."}

        try:
            executor = self._build_agent(user_id, context)

            async for chunk in executor.astream({"input": enriched_task}):
                if "intermediate_step" in chunk:
                    for action, observation in chunk["intermediate_step"]:
                        tool_name = getattr(action, "tool", "unknown")
                        yield {
                            "type": _infer_step_type(tool_name),
                            "tool": tool_name,
                            "message": str(observation)[:300],
                        }
                elif "output" in chunk:
                    await self._store_memory(user_id, f"Task: {task}\nOutcome: {chunk['output'][:300]}")
                    yield {"type": "complete", "message": chunk["output"]}

        except Exception as e:
            yield {"type": "error", "message": str(e)}

    async def get_memories(self, user_id: str) -> List[MemoryItem]:
        """Get all memories for a user."""
        try:
            results = self.memory.get_all(user_id=user_id)
            memories = []
            for m in (results.get("results") or []):
                memories.append(MemoryItem(
                    id=m.get("id", str(uuid.uuid4())),
                    user_id=user_id,
                    content=m.get("memory", ""),
                    category=_categorize_memory(m.get("memory", "")),
                    created_at=datetime.utcnow(),
                ))
            return memories
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []

    async def delete_memory(self, user_id: str, memory_id: str):
        """Delete a memory."""
        self.memory.delete(memory_id=memory_id)

    async def get_signals(self, user_id: str, query: Optional[str] = None) -> List[SignalItem]:
        """Get cached signals for a user."""
        return self._signals_store.get(user_id, [])

    async def get_action_history(self, user_id: str) -> List[ActionItem]:
        """Get action history for a user."""
        return self._actions_store.get(user_id, [])


def _infer_step_type(tool_name: str) -> str:
    tool_name = tool_name.lower()
    if "tavily" in tool_name or "search" in tool_name:
        return "search"
    if any(x in tool_name for x in ["github", "slack", "notion", "gmail", "composio"]):
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
