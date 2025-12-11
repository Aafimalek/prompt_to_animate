"""
Pydantic Models for MongoDB Documents

Defines data schemas for chat history and related entities.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic compatibility."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v, handler=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string"}


class ChatCreate(BaseModel):
    """Schema for creating a new chat."""
    clerk_id: str = Field(..., description="Clerk user ID")
    prompt: str = Field(..., description="User's prompt")
    length: str = Field(default="Short (5s)", description="Video length setting")
    video_url: str = Field(..., description="CloudFront signed URL for the video")
    s3_key: str = Field(..., description="S3 object key for regenerating URLs")
    code: str = Field(..., description="Generated Manim code")


class ChatInDB(BaseModel):
    """Schema for chat stored in MongoDB."""
    id: str = Field(alias="_id")
    clerk_id: str
    prompt: str
    length: str
    video_url: str
    s3_key: str
    code: str
    created_at: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }


class ChatResponse(BaseModel):
    """Schema for chat response to frontend."""
    id: str
    prompt: str
    length: str
    video_url: str
    code: str
    created_at: str  # ISO format string
    
    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    """Schema for list of chats response."""
    chats: list[ChatResponse]
    total: int
