from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_gemini_client
from app.schemas.agent import ChatRequest, ChatResponse, ExtractRequest, ExtractResponse
from services.llm import GeminiClient

router = APIRouter(tags=["agent"])


@router.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(
    request: ChatRequest,
    client: Annotated[GeminiClient, Depends(get_gemini_client)] = None,
):
    return client.chat(request.prompt, request.context or "")


@router.post("/agent/extract", response_model=ExtractResponse)
async def extract_data(
    request: ExtractRequest,
    client: Annotated[GeminiClient, Depends(get_gemini_client)] = None,
):
    return client.extract_structured_data(request.text, request.schema_description)
