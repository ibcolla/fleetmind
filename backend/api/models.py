from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class RunAgentRequest(BaseModel):
    task: str
    user_id: str = "default"
    context: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "task": "Monitor my competitors and create a GitHub issue if they launch anything new",
                "user_id": "founder_123",
                "context": {
                    "startup_name": "FleetMind",
                    "competitors": ["linear.app", "notion.so"],
                    "keywords": ["project management", "AI ops"],
                }
            }
        }


class AgentStep(BaseModel):
    step_type: str  # "search", "reason", "remember", "act"
    content: str
    tool_used: Optional[str] = None
    timestamp: datetime = None

    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow()
        super().__init__(**data)


class AgentResponse(BaseModel):
    task: str
    user_id: str
    status: str  # "completed", "failed", "partial"
    summary: str
    steps: List[AgentStep]
    signals_found: int
    actions_taken: int
    memories_stored: int
    duration_ms: int
    timestamp: datetime = None

    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow()
        super().__init__(**data)


class MemoryItem(BaseModel):
    id: str
    user_id: str
    content: str
    category: str  # "competitor", "decision", "context", "preference"
    created_at: datetime
    relevance_score: Optional[float] = None


class SignalItem(BaseModel):
    id: str
    title: str
    url: str
    snippet: str
    source: str
    signal_type: str  # "competitor", "market", "tech", "mention"
    importance: str  # "high", "medium", "low"
    discovered_at: datetime


class ActionItem(BaseModel):
    id: str
    user_id: str
    action_type: str  # "github_issue", "slack_message", "notion_page", "email_draft"
    description: str
    tool: str
    status: str  # "completed", "failed"
    result: Optional[Dict[str, Any]] = None
    executed_at: datetime
