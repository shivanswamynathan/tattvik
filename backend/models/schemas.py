from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class TopicResponse(BaseModel):
    topics: List[Dict[str, Any]]

class RevisionRequest(BaseModel):
    topic: str
    query: Optional[str] = None
    session_id: str
    student_id: str
    conversation_count: int = 0

class RevisionResponse(BaseModel):
    response: str
    topic: str
    session_id: str
    conversation_count: int
    is_session_complete: bool
    session_summary: Optional[str] = None
    next_suggested_action: Optional[str] = None
    sources: List[str] = []
    current_stage: Optional[str] = None
    timestamp: datetime

class SessionState(BaseModel):
    session_id: str
    topic: str
    student_id: str
    conversation_count: int
    started_at: datetime
    last_interaction: datetime
    is_complete: bool = False
    key_concepts_covered: List[str] = []
    user_understanding_level: str = "beginner"