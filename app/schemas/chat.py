from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class DateRange(BaseModel):
    start_year: int
    end_year: int

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = []
    date_range: Optional[DateRange] = None

class Source(BaseModel):
    filename: str
    page: Optional[int] = None
    document_type: str
    relevance: str = "high"

class ChartDataset(BaseModel):
    label: Optional[str] = None
    data: List[float]

class ChartData(BaseModel):
    labels: List[str]
    datasets: List[ChartDataset]

class Chart(BaseModel):
    type: str  # "line", "bar", "pie"
    title: str
    data: ChartData

class ChatResponse(BaseModel):
    response: str
    sources: List[Source]
    tokens_used: int
    chart: Optional[Dict[str, Any]] = None
    agents_used: Optional[List[str]] = None
    analysis: Optional[Dict[str, Any]] = None
    conversation_id: Optional[int] = None

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int
    tokens_used: int

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime
    tokens_used: Optional[int]
    sources: Optional[List[Dict]]
    chart_data: Optional[Dict]
    agents_used: Optional[List[str]]

    class Config:
        from_attributes = True

class ConversationWithMessages(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]
