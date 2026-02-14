from gtts import gTTS
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
import io
import os

def text_to_speech_stream(text: str, lang: str = "en", voice: str = "alloy"):
    """
    Generates MP3 audio from text.
    High Quality: Uses OpenAI TTS if OPENAI_API_KEY is present.
    Fallback: Uses gTTS (Google Translate) if no key.
    
    Voices (OpenAI): alloy, echo, fable, onyx, nova, shimmer
    """
    if not text:
        return None
    
    # 1. Try OpenAI TTS (Human-like)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and OpenAI:
        try:
            client = OpenAI(api_key=api_key)
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            # Response content is binary audio
            audio_stream = io.BytesIO(response.content)
            audio_stream.seek(0)
            return audio_stream
        except Exception as e:
            print(f"OpenAI TTS Error: {e}. Falling back to gTTS.")
            
    # 2. Fallback to gTTS (Robotic but free)
    try:
        tts = gTTS(text=text, lang=lang)
        audio_stream = io.BytesIO()
        tts.write_to_fp(audio_stream)
        audio_stream.seek(0)
        return audio_stream
    except Exception as e:
        print(f"gTTS Error: {e}")
        return None
