import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    BaseSettings = BaseModel
    SettingsConfigDict = ConfigDict
    HAS_PYDANTIC_SETTINGS = False

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    gemini_api_key: Optional[str] = Field(default=None, validation_alias="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    database_url: Optional[str] = Field(default=None, validation_alias="DATABASE_URL")

    yolo_frame_stride: int = Field(default=2, validation_alias="SPATIAL_YOLO_FRAME_STRIDE")
    gemini_frame_stride: int = Field(default=3, validation_alias="SPATIAL_GEMINI_FRAME_STRIDE")
    max_gemini_crops: int = Field(default=3, validation_alias="SPATIAL_MAX_GEMINI_CROPS")
    fallback_key_bucket_px: int = Field(default=96, validation_alias="SPATIAL_FALLBACK_KEY_BUCKET_PX")
    gemini_label_ttl_sec: float = Field(default=20.0, validation_alias="SPATIAL_GEMINI_LABEL_TTL_SEC")
    detect_conf: float = Field(default=0.35, validation_alias="SPATIAL_DETECT_CONF")
    max_detections: int = Field(default=30, validation_alias="SPATIAL_MAX_DETECTIONS")
    model_imgsz: int = Field(default=640, validation_alias="SPATIAL_MODEL_IMGSZ")
    use_tracking: bool = Field(default=True, validation_alias="SPATIAL_USE_TRACKING")
    target_classes: str = Field(
        default="0,24,26,28,39,41,56,57,58,59,60,62,63,64,65,66,67,73,74",
        validation_alias="SPATIAL_TARGET_CLASSES",
    )

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
