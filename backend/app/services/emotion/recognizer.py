"""
Emotion Recognition Service.

Uses a pretrained HuggingFace speech emotion recognition model via the
transformers pipeline API. The model is loaded ONCE at startup and reused
for all subsequent requests.

Supported model: ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition
Alternate:        superb/wav2vec2-base-superb-er (faster, lower accuracy)

Model labels are mapped deterministically to AutoAce emotion categories:
  neutral, satisfied, frustrated, upset, distressed
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np

from app.config import Settings
from app.schemas.models import EmotionalIntensity, EmotionalTone

logger = logging.getLogger(__name__)


# Deterministic mapping from model label → AutoAce emotion
# Add more source labels as needed when switching models
_LABEL_MAP: Dict[str, EmotionalTone] = {
    # ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition labels
    "angry": EmotionalTone.frustrated,
    "disgust": EmotionalTone.upset,
    "fear": EmotionalTone.distressed,
    "happy": EmotionalTone.satisfied,
    "neutral": EmotionalTone.neutral,
    "ps": EmotionalTone.satisfied,       # pleasant surprise
    "sad": EmotionalTone.upset,
    "boredom": EmotionalTone.neutral,
    "calm": EmotionalTone.neutral,
    # superb/wav2vec2-base-superb-er labels
    "hap": EmotionalTone.satisfied,
    "ang": EmotionalTone.frustrated,
    "sad": EmotionalTone.upset,
    "neu": EmotionalTone.neutral,
    "exc": EmotionalTone.distressed,     # excited (high arousal)
    "fru": EmotionalTone.frustrated,
    "fea": EmotionalTone.distressed,
    "sur": EmotionalTone.satisfied,
    "dis": EmotionalTone.upset,
    # Additional common labels
    "frustrated": EmotionalTone.frustrated,
    "satisfied": EmotionalTone.satisfied,
    "distressed": EmotionalTone.distressed,
    "upset": EmotionalTone.upset,
}

# Intensity thresholds based on model confidence
_INTENSITY_THRESHOLDS = {
    EmotionalIntensity.low: 0.0,     # 0.0 – 0.5
    EmotionalIntensity.medium: 0.5,  # 0.5 – 0.75
    EmotionalIntensity.high: 0.75,   # 0.75 – 1.0
}


def _map_label(label: str) -> EmotionalTone:
    """Map a raw model label to an AutoAce EmotionalTone (case-insensitive)."""
    normalized = label.strip().lower()
    if normalized in _LABEL_MAP:
        return _LABEL_MAP[normalized]
    # Partial match fallback
    for key, tone in _LABEL_MAP.items():
        if key in normalized or normalized in key:
            return tone
    logger.warning(f"Unknown emotion label '{label}', defaulting to neutral")
    return EmotionalTone.neutral


def _score_to_intensity(score: float, tone: EmotionalTone) -> EmotionalIntensity:
    """
    Convert model confidence score to intensity.
    Neutral emotions are capped at medium intensity.
    """
    if tone == EmotionalTone.neutral:
        return EmotionalIntensity.low if score < 0.7 else EmotionalIntensity.medium

    if score >= _INTENSITY_THRESHOLDS[EmotionalIntensity.high]:
        return EmotionalIntensity.high
    elif score >= _INTENSITY_THRESHOLDS[EmotionalIntensity.medium]:
        return EmotionalIntensity.medium
    else:
        return EmotionalIntensity.low


class EmotionRecognizer:
    """
    Wraps a HuggingFace audio-classification pipeline for speech emotion recognition.
    Thread-safe for concurrent inference calls.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._pipeline: Optional[Any] = None
        self._loaded = False

    async def load(self) -> None:
        """
        Load the model into memory. Called once during FastAPI startup.
        Runs in an executor to avoid blocking the event loop.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_sync)

    def _load_sync(self) -> None:
        """Synchronous model load — runs in thread pool."""
        from transformers import pipeline

        model_name = self.settings.emotion_model_name
        cache_dir = self.settings.emotion_model_cache_dir

        logger.info(f"Loading emotion model: {model_name}")
        kwargs: Dict[str, Any] = {
            "model": model_name,
            "cache_dir": cache_dir,
        }

        if self.settings.huggingface_token:
            kwargs["token"] = self.settings.huggingface_token

        try:
            import torch
            device = 0 if torch.cuda.is_available() else -1
            kwargs["device"] = device
            if device == 0:
                logger.info("GPU available — emotion model on CUDA")
            else:
                logger.info("No GPU detected — emotion model on CPU")
        except ImportError:
            pass

        self._pipeline = pipeline("audio-classification", **kwargs)
        self._loaded = True
        logger.info(f"Emotion model loaded: {model_name}")

    def predict(
        self, waveform: np.ndarray, sample_rate: int
    ) -> Tuple[EmotionalTone, EmotionalIntensity, float]:
        """
        Run emotion inference on a preprocessed waveform.

        Args:
            waveform: Mono float32 numpy array.
            sample_rate: Sample rate of the waveform.

        Returns:
            Tuple of (emotional_tone, emotional_intensity, model_confidence)
        """
        if not self._loaded or self._pipeline is None:
            logger.warning("Emotion model not loaded — returning default")
            return EmotionalTone.neutral, EmotionalIntensity.low, 0.3

        try:
            # Cap waveform duration to max 30s for emotion model to avoid long inference/chunking
            max_samples = sample_rate * 30
            if len(waveform) > max_samples:
                waveform = waveform[:max_samples]

            # HuggingFace pipeline accepts raw numpy arrays with sampling_rate
            results = self._pipeline(
                {"raw": waveform, "sampling_rate": sample_rate},
                top_k=None,
            )

            if not results:
                return EmotionalTone.neutral, EmotionalIntensity.low, 0.3

            # Sort by score descending
            results_sorted = sorted(results, key=lambda x: x["score"], reverse=True)
            top = results_sorted[0]

            tone = _map_label(top["label"])
            confidence = float(top["score"])
            intensity = _score_to_intensity(confidence, tone)

            logger.debug(
                f"Emotion: {tone} | Intensity: {intensity} | Confidence: {confidence:.3f} "
                f"| Raw label: {top['label']}"
            )
            return tone, intensity, confidence

        except Exception as exc:
            logger.error(f"Emotion inference failed: {exc}", exc_info=True)
            return EmotionalTone.neutral, EmotionalIntensity.low, 0.3
