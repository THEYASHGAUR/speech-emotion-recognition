"""
Application configuration using Pydantic BaseSettings.
All values are read from environment variables with sensible defaults.
No hardcoded constants should exist elsewhere in the codebase.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ─────────────────────────── App ────────────────────────────
    app_name: str = Field("AutoAce AI", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    debug: bool = Field(False, env="DEBUG")
    environment: str = Field("production", env="ENVIRONMENT")

    # ─────────────────────────── API ────────────────────────────
    api_prefix: str = Field("/api/v1", env="API_PREFIX")
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "http://127.0.0.1:3000"],
        env="CORS_ORIGINS",
    )

    # ─────────────────────── Authentication ─────────────────────
    auth_username: str = Field("admin", env="AUTH_USERNAME")
    auth_password: str = Field("autoace2024", env="AUTH_PASSWORD")
    secret_key: str = Field(
        "change-me-in-production-use-a-strong-random-secret-key",
        env="SECRET_KEY",
    )
    token_expire_hours: int = Field(24, env="TOKEN_EXPIRE_HOURS")

    # ─────────────────────────── Upload ─────────────────────────
    upload_dir: str = Field("./uploads", env="UPLOAD_DIR")
    max_upload_size_mb: int = Field(500, env="MAX_UPLOAD_SIZE_MB")
    allowed_audio_extensions: List[str] = Field(
        [".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".webm", ".opus"],
        env="ALLOWED_AUDIO_EXTENSIONS",
    )

    # ──────────────────────── Audio Processing ───────────────────
    target_sample_rate: int = Field(16000, env="TARGET_SAMPLE_RATE")
    max_audio_duration_seconds: int = Field(600, env="MAX_AUDIO_DURATION_SECONDS")

    # ──────────────────────── Emotion Model ──────────────────────
    emotion_model_name: str = Field(
        "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition",
        env="EMOTION_MODEL_NAME",
    )
    emotion_model_cache_dir: str = Field("./models/emotion", env="EMOTION_MODEL_CACHE_DIR")

    # ───────────────────── Silence Detection ─────────────────────
    silence_threshold_db: float = Field(-40.0, env="SILENCE_THRESHOLD_DB")
    long_silence_min_duration_seconds: float = Field(2.0, env="LONG_SILENCE_MIN_DURATION_SECONDS")

    # ──────────────────────── Noise Detection ────────────────────
    noise_snr_threshold_db: float = Field(20.0, env="NOISE_SNR_THRESHOLD_DB")
    noise_severity_low_snr: float = Field(25.0, env="NOISE_SEVERITY_LOW_SNR")
    noise_severity_high_snr: float = Field(15.0, env="NOISE_SEVERITY_HIGH_SNR")

    # ─────────────────────── Quality Analysis ────────────────────
    quality_snr_clear_threshold: float = Field(25.0, env="QUALITY_SNR_CLEAR_THRESHOLD")
    quality_snr_impaired_threshold: float = Field(15.0, env="QUALITY_SNR_IMPAIRED_THRESHOLD")
    quality_clipping_threshold: float = Field(0.98, env="QUALITY_CLIPPING_THRESHOLD")
    quality_clipping_ratio_max: float = Field(0.001, env="QUALITY_CLIPPING_RATIO_MAX")

    # ─────────────────────── Overlap Detection ───────────────────
    overlap_energy_threshold: float = Field(0.02, env="OVERLAP_ENERGY_THRESHOLD")
    overlap_frame_length: int = Field(2048, env="OVERLAP_FRAME_LENGTH")
    overlap_hop_length: int = Field(512, env="OVERLAP_HOP_LENGTH")
    overlap_min_duration_seconds: float = Field(0.5, env="OVERLAP_MIN_DURATION_SECONDS")

    # ─────────────────────── Confidence Score ────────────────────
    confidence_model_weight: float = Field(0.6, env="CONFIDENCE_MODEL_WEIGHT")
    confidence_feature_weight: float = Field(0.25, env="CONFIDENCE_FEATURE_WEIGHT")
    confidence_heuristic_weight: float = Field(0.15, env="CONFIDENCE_HEURISTIC_WEIGHT")
    confidence_min_duration_seconds: float = Field(1.0, env="CONFIDENCE_MIN_DURATION_SECONDS")

    # ─────────────────────── Processing ──────────────────────────
    max_concurrent_files: int = Field(4, env="MAX_CONCURRENT_FILES")
    processing_timeout_seconds: int = Field(120, env="PROCESSING_TIMEOUT_SECONDS")

    # ─────────────────────── HuggingFace ─────────────────────────
    huggingface_token: str = Field("", env="HUGGINGFACE_TOKEN")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance (singleton)."""
    return Settings()
