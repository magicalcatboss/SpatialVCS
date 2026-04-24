from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
    context: Optional[str] = ""


class ChatResponse(BaseModel):
    text: Optional[str] = None
    error: Optional[str] = None


class ExtractRequest(BaseModel):
    text: str
    schema_description: str


class ExtractResponse(BaseModel):
    data: Optional[str] = None
    error: Optional[str] = None
