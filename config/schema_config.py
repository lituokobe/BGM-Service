from typing import Generic, TypeVar
from pydantic import BaseModel, Field

class SummarizeBGMRequest(BaseModel):
    bgm_path: str = Field(..., description="Path to audio file")

class BGMSummary(BaseModel):
    """Response model for BGM summarization."""
    overall_summary: str = Field(..., description="Natural language summary of the music")
    duration: float = Field(default=0.0)

# API response schema
T = TypeVar("T")
class APIResponse(BaseModel, Generic[T]):
    """Unified API response wrapper"""
    success: bool = Field(..., description="Whether the request succeeded")
    data: T|None = Field(default=None, description="Response payload on success")
    error: str|None = Field(default=None, description="Error message on failure")
    error_code: str|None = Field(default=None, description="Machine-readable error code")

    @classmethod
    def ok(cls, data: T) -> "APIResponse[T]":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str, error_code: str = "UNKNOWN") -> "APIResponse[T]":
        return cls(success=False, error=error, error_code=error_code)