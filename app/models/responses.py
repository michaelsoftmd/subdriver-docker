from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime

class BaseResponse(BaseModel):
    """Base response model"""
    status: str = Field(..., description="Status: success or error")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Any] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class NavigationResponse(BaseModel):
    """Navigation response"""
    url: str
    title: str
    status: str = "success"

class ClickResponse(BaseModel):
    """Click response"""
    status: str = "success"
    selector: Optional[str] = None
    text: Optional[str] = None

class ExtractResponse(BaseModel):
    """Extract response"""
    status: str = "success"
    count: int
    data: Any
