from typing import Optional

from pydantic import BaseModel


class SpeakRequest(BaseModel):
    text: str
    lang: str = "en"


class TranscriptionResponse(BaseModel):
    text: Optional[str] = None
    source: Optional[str] = None
    error: Optional[str] = None
