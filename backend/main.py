"""
FleetMind - AI Ops Agent for Solo Founders
FastAPI Backend
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import json
import logging
from datetime import datetime

from agents.fleet_agent import FleetMindAgent
from api.models import (
    RunAgentRequest,
    AgentResponse,
    MemoryItem,
    SignalItem,
    ActionItem,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FleetMind API",
    description="AI Ops Agent for Solo Founders",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = FleetMindAgent()


@app.get("/")
async def root():
    return {"status": "FleetMind is running", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/agent/run", response_model=AgentResponse)
async def run_agent(request: RunAgentRequest):
    """
    Run the FleetMind agent with a given task.
    The agent will: search signals → reason → remember → act.
    """
    try:
        result = await agent.run(
            task=request.task,
            user_id=request.user_id,
            context=request.context,
        )
        return result
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/stream")
async def stream_agent(request: RunAgentRequest):
    """
    Stream agent reasoning steps in real-time via SSE.
    """
    async def event_generator():
        async for step in agent.stream(
            task=request.task,
            user_id=request.user_id,
            context=request.context,
        ):
            yield f"data: {json.dumps(step)}\n\n"
            await asyncio.sleep(0.05)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/memory/{user_id}", response_model=List[MemoryItem])
async def get_memories(user_id: str):
    """Retrieve stored memories for a user/startup."""
    try:
        memories = await agent.get_memories(user_id)
        return memories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memory/{user_id}/{memory_id}")
async def delete_memory(user_id: str, memory_id: str):
    """Delete a specific memory."""
    try:
        await agent.delete_memory(user_id, memory_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/signals/{user_id}", response_model=List[SignalItem])
async def get_signals(user_id: str, query: Optional[str] = None):
    """Get latest market signals for a user's startup context."""
    try:
        signals = await agent.get_signals(user_id, query)
        return signals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/actions/{user_id}", response_model=List[ActionItem])
async def get_actions(user_id: str):
    """Get history of actions taken by the agent."""
    try:
        actions = await agent.get_action_history(user_id)
        return actions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
