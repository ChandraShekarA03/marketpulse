import json
import re
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.agent import AgentConversation, AgentMemory

TICKER_PATTERN = re.compile(r"\b[A-Z]{2,5}\b")


def save_agent_conversation(
    db: Session,
    user_id: int,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> AgentConversation:
    conversation = AgentConversation(
        user_id=user_id,
        role=role,
        content=content,
        extra_metadata=json.dumps(metadata) if metadata else None,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_agent_history(db: Session, user_id: int, limit: int = 12) -> List[Dict[str, Any]]:
    entries = (
        db.query(AgentConversation)
        .filter(AgentConversation.user_id == user_id)
        .order_by(AgentConversation.created_at.desc())
        .limit(limit)
        .all()
    )
    history = []
    for entry in reversed(entries):
        history.append(
            {
                "id": entry.id,
                "role": entry.role,
                "content": entry.content,
                "metadata": json.loads(entry.extra_metadata) if entry.extra_metadata else None,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            }
        )
    return history


def get_agent_memory(db: Session, user_id: int, limit: int = 6) -> List[Dict[str, Any]]:
    memories = (
        db.query(AgentMemory)
        .filter(AgentMemory.user_id == user_id)
        .order_by(AgentMemory.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": memory.id,
            "topic": memory.topic,
            "summary": memory.summary,
            "created_at": memory.created_at.isoformat() if memory.created_at else None,
        }
        for memory in memories
    ]


def update_agent_memory(db: Session, user_id: int, topic: str, summary: str) -> AgentMemory:
    memory = AgentMemory(user_id=user_id, topic=topic, summary=summary)
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def extract_primary_ticker(text: str, fallback_symbols: Optional[List[str]] = None) -> Optional[str]:
    candidates = TICKER_PATTERN.findall(text or "")
    if candidates:
        return candidates[0]
    if fallback_symbols:
        return fallback_symbols[0]
    return None


def build_memory_summary(query: str, response: str) -> str:
    ticker = extract_primary_ticker(query)
    topic = ticker or "portfolio strategy"
    summary = response.strip().replace("\n", " ")
    return f"{topic}: {summary[:220]}"
