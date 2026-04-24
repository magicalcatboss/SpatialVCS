from typing import Any, Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import get_gemini_client
from services.llm import GeminiClient
from services.vision import analyze_face_image

router = APIRouter(tags=["vision"])


@router.post("/vision/face-analysis", response_model=dict[str, Any])
async def analyze_face(file: UploadFile = File(...)):
    contents = await file.read()
    return analyze_face_image(contents)


@router.post("/vision/describe", response_model=dict[str, Any])
async def describe_scene(
    file: UploadFile = File(...),
    client: Annotated[GeminiClient, Depends(get_gemini_client)] = None,
):
    contents = await file.read()
    return client.describe_image(contents)
