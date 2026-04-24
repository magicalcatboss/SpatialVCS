import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    BaseSettings = BaseModel
    SettingsConfigDict = ConfigDict
    HAS_PYDANTIC_SETTINGS = False

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    database_url: Optional[str] = None

    yolo_frame_stride: int = 2
    gemini_frame_stride: int = 3
    max_gemini_crops: int = 3
    fallback_key_bucket_px: int = 96
    gemini_label_ttl_sec: float = 20.0
    detect_conf: float = 0.35
    max_detections: int = 30
    model_imgsz: int = 640
    use_tracking: bool = True
    target_classes: str = "0,24,26,28,39,41,56,57,58,59,60,62,63,64,65,66,67,73,74"

    @classmethod
    def from_env(cls) -> "Settings":
        values = {
            "gemini_api_key": os.getenv("GEMINI_API_KEY"),
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "database_url": os.getenv("DATABASE_URL"),
            "yolo_frame_stride": int(os.getenv("SPATIAL_YOLO_FRAME_STRIDE", "2")),
            "gemini_frame_stride": int(os.getenv("SPATIAL_GEMINI_FRAME_STRIDE", "3")),
            "max_gemini_crops": int(os.getenv("SPATIAL_MAX_GEMINI_CROPS", "3")),
            "fallback_key_bucket_px": int(os.getenv("SPATIAL_FALLBACK_KEY_BUCKET_PX", "96")),
            "gemini_label_ttl_sec": float(os.getenv("SPATIAL_GEMINI_LABEL_TTL_SEC", "20")),
            "detect_conf": float(os.getenv("SPATIAL_DETECT_CONF", "0.35")),
            "max_detections": int(os.getenv("SPATIAL_MAX_DETECTIONS", "30")),
            "model_imgsz": int(os.getenv("SPATIAL_MODEL_IMGSZ", "640")),
            "use_tracking": os.getenv("SPATIAL_USE_TRACKING", "1").strip().lower() not in {"0", "false", "no"},
            "target_classes": os.getenv(
                "SPATIAL_TARGET_CLASSES",
                "0,24,26,28,39,41,56,57,58,59,60,62,63,64,65,66,67,73,74",
            ),
        }
        return cls(**values)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    if HAS_PYDANTIC_SETTINGS:
        return Settings()
    return Settings.from_env()
