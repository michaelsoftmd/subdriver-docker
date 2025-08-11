from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Optional, List, Dict, Any
import re

class NavigationRequest(BaseModel):
    """Navigation request with validation"""
    url: HttpUrl | str
    wait_for: Optional[str] = Field(None, max_length=500)
    wait_timeout: int = Field(10, ge=1, le=60)
    
    @validator('url')
    def validate_url(cls, v):
        # Block potentially dangerous URLs
        blocked_patterns = [
            r'javascript:',
            r'data:',
            r'file://',
            r'chrome://',
            r'about:config'
        ]
        
        url_str = str(v).lower()
        for pattern in blocked_patterns:
            if re.match(pattern, url_str):
                raise ValueError(f"Blocked URL pattern: {pattern}")
        
        # Add https if no protocol
        if isinstance(v, str) and not v.startswith(('http://', 'https://')):
            v = f'https://{v}'
        
        return v
    
    @validator('wait_for')
    def validate_selector(cls, v):
        if v:
            # Basic XSS prevention in selectors
            dangerous_patterns = ['<script', 'javascript:', 'onerror=']
            for pattern in dangerous_patterns:
                if pattern in v.lower():
                    raise ValueError(f"Invalid selector: contains {pattern}")
        return v

class SubstackRequest(BaseModel):
    """Substack-specific request validation"""
    publication_url: HttpUrl
    max_posts: int = Field(20, ge=1, le=100)
    
    @validator('publication_url')
    def validate_substack_url(cls, v):
        url_str = str(v)
        if 'substack.com' not in url_str:
            raise ValueError("Must be a Substack URL")
        return v

class TypeRequest(BaseModel):
    """Type text request with content validation"""
    text: str = Field(..., min_length=1, max_length=10000)
    selector: Optional[str] = Field(None, max_length=500)
    
    @validator('text')
    def validate_text_content(cls, v):
        # Prevent injection of control characters
        control_chars = ['\x00', '\x1b', '\x7f']
        for char in control_chars:
            if char in v:
                raise ValueError("Text contains invalid control characters")
        return v
