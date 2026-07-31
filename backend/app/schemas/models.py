"""
Pydantic schemas for all API request/response models.
All schemas use strict type hints and field validation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────── Enums ───────────────────────────────────────────


class EmotionalTone(str, Enum):
    neutral = "neutral"
    satisfied = "satisfied"
    frustrated = "frustrated"
    upset = "upset"
    distressed = "distressed"


class EmotionalIntensity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class NoiseType(str, Enum):
    office_chatter = "office_chatter"
    road_noise = "road_noise"
    music = "music"
    wind = "wind"
    keyboard = "keyboard"
    television = "television"
    mechanical = "mechanical"
    none = "none"


class NoiseSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    none = "none"


class AudioQuality(str, Enum):
    clear = "clear"
    slightly_impaired = "slightly_impaired"
    severely_impaired = "severely_impaired"


class BatchStatus(str, Enum):
    uploading = "uploading"
    validating = "validating"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    partial = "partial"


class FileStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


# ─────────────────────────── Audio Analysis ──────────────────────────────────


class AudioAnalysis(BaseModel):
    """Core prediction output — exactly matches the assignment schema."""

    emotional_tone: EmotionalTone
    emotional_intensity: EmotionalIntensity
    background_noise_present: bool
    background_noise_type: NoiseType
    background_noise_severity: NoiseSeverity
    audio_quality: AudioQuality
    speaker_overlap_present: bool
    long_silence_present: bool
    confidence: float = Field(..., ge=0.0, le=1.0)


class FileResult(BaseModel):
    """Result for a single audio file in a batch."""

    filename: str
    status: FileStatus
    analysis: Optional[AudioAnalysis] = None
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    audio_duration_seconds: Optional[float] = None


# ─────────────────────────── Batch Models ────────────────────────────────────


class BatchSummary(BaseModel):
    """Summary statistics for a completed batch."""

    total_files: int
    completed_files: int
    failed_files: int
    avg_confidence: Optional[float] = None
    emotion_distribution: Dict[str, int] = Field(default_factory=dict)
    quality_distribution: Dict[str, int] = Field(default_factory=dict)
    processing_time_seconds: Optional[float] = None


class BatchResponse(BaseModel):
    """Full batch status and results."""

    batch_id: str
    status: BatchStatus
    created_at: datetime
    updated_at: datetime
    total_files: int
    completed_files: int
    failed_files: int
    results: List[FileResult] = Field(default_factory=list)
    summary: Optional[BatchSummary] = None
    validation_errors: List[str] = Field(default_factory=list)


class BatchListItem(BaseModel):
    """Lightweight batch info for history listing."""

    batch_id: str
    status: BatchStatus
    created_at: datetime
    updated_at: datetime
    total_files: int
    completed_files: int
    failed_files: int


# ─────────────────────────── Upload ──────────────────────────────────────────


class UploadResponse(BaseModel):
    """Response after a successful batch upload."""

    batch_id: str
    message: str
    total_files: int
    validation_errors: List[str] = Field(default_factory=list)


# ─────────────────────────── Auth ────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# ─────────────────────────── Errors ──────────────────────────────────────────


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
    path: Optional[str] = None
