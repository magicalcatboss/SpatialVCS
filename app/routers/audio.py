from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.dependencies import get_gemini_client
from app.schemas.audio import SpeakRequest, TranscriptionResponse
from services.audio import text_to_speech_stream
from services.llm import GeminiClient

router = APIRouter(tags=["audio"])


@router.post("/audio/speak")
async def speak(request: SpeakRequest):
    audio_stream = text_to_speech_stream(request.text, request.lang)
    if not audio_stream:
        raise HTTPException(status_code=500, detail="TTS Generation failed")
    return StreamingResponse(audio_stream, media_type="audio/mpeg")


@router.post("/audio/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    client: Annotated[GeminiClient, Depends(get_gemini_client)] = None,
):
    contents = await file.read()

    mime_map = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "webm": "audio/webm",
        "ogg": "audio/ogg",
        "m4a": "audio/mp4",
    }
    ext = (file.filename or "audio.wav").rsplit(".", 1)[-1].lower()
    mime_type = mime_map.get(ext, "audio/wav")

    return client.transcribe_audio(contents, mime_type)
