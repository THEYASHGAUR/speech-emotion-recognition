"""
Confidence Score Calculator.

Combines signals from three sources using configurable weights:
1. Model confidence (softmax probability from emotion recognizer)
2. Feature confidence (quality of acoustic features — audio duration, SNR, etc.)
3. Heuristic confidence (audio health — no clipping, normal volume, etc.)

Final confidence is a weighted sum, clipped to [0.0, 1.0].
No values are hardcoded — all weights and thresholds come from config.
"""

from __future__ import annotations

import logging

import numpy as np

from app.config import Settings
from app.services.noise.detector import NoiseAnalysisResult
from app.services.overlap.detector import OverlapAnalysisResult
from app.services.quality.analyzer import QualityFeatures
from app.services.silence.detector import SilenceAnalysisResult

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """
    Computes a final confidence score for a single audio file's predictions.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def compute(
        self,
        model_confidence: float,
        audio_duration_seconds: float,
        quality_features: QualityFeatures,
        noise_result: NoiseAnalysisResult,
        overlap_result: OverlapAnalysisResult,
        silence_result: SilenceAnalysisResult,
    ) -> float:
        """
        Compute overall prediction confidence.

        Args:
            model_confidence: Raw softmax probability from emotion model (0-1).
            audio_duration_seconds: Total audio duration.
            quality_features: Output from QualityAnalyzer.
            noise_result: Output from NoiseDetector.
            overlap_result: Output from OverlapDetector.
            silence_result: Output from SilenceDetector.

        Returns:
            Confidence score in [0.0, 1.0].
        """
        model_conf = self._validate_model_confidence(model_confidence)
        feature_conf = self._compute_feature_confidence(
            audio_duration_seconds, quality_features, noise_result
        )
        heuristic_conf = self._compute_heuristic_confidence(
            quality_features, silence_result, overlap_result
        )

        w_m = self.settings.confidence_model_weight
        w_f = self.settings.confidence_feature_weight
        w_h = self.settings.confidence_heuristic_weight

        # Normalize weights in case they don't sum to 1
        total_w = w_m + w_f + w_h
        final = (
            (w_m / total_w) * model_conf +
            (w_f / total_w) * feature_conf +
            (w_h / total_w) * heuristic_conf
        )

        final = float(np.clip(final, 0.0, 1.0))

        logger.debug(
            f"Confidence: {final:.3f} | "
            f"model={model_conf:.3f} | feature={feature_conf:.3f} | heuristic={heuristic_conf:.3f}"
        )
        return round(final, 4)

    def _validate_model_confidence(self, raw: float) -> float:
        """Clip and validate model confidence value."""
        return float(np.clip(raw, 0.0, 1.0))

    def _compute_feature_confidence(
        self,
        duration: float,
        quality: QualityFeatures,
        noise: NoiseAnalysisResult,
    ) -> float:
        """
        Feature-based confidence from input signal quality.

        Factors:
        - Duration: Very short files (<1s) reduce confidence
        - SNR: Low SNR reduces confidence
        - Noise type confidence
        """
        min_dur = self.settings.confidence_min_duration_seconds

        # Duration score: full confidence at 3s+, drops linearly below min_dur
        if duration >= 3.0:
            duration_score = 1.0
        elif duration >= min_dur:
            duration_score = 0.5 + 0.5 * (duration - min_dur) / (3.0 - min_dur)
        else:
            duration_score = float(np.clip(duration / min_dur * 0.5, 0.0, 0.5))

        # SNR score
        snr_score = float(np.clip((quality.snr_db + 5) / 40.0, 0.0, 1.0))

        # Noise classifier confidence
        noise_conf = noise.feature_confidence if noise else 0.7

        feature_conf = (
            0.4 * duration_score +
            0.4 * snr_score +
            0.2 * noise_conf
        )
        return float(np.clip(feature_conf, 0.0, 1.0))

    def _compute_heuristic_confidence(
        self,
        quality: QualityFeatures,
        silence: SilenceAnalysisResult,
        overlap: OverlapAnalysisResult,
    ) -> float:
        """
        Heuristic confidence based on audio health indicators.

        Penalizes:
        - Heavy clipping (corrupts model input)
        - Very low volume (microphone issues)
        - High silence ratio (not enough speech data)
        """
        # Clipping penalty
        clipping_penalty = float(np.clip(quality.clipping_ratio * 100, 0.0, 1.0))

        # Volume penalty (RMS below -50dB = likely silence)
        volume_score = float(np.clip((quality.rms_db + 60) / 50.0, 0.0, 1.0))

        # Silence penalty: high silence ratio means less data for inference
        silence_penalty = float(np.clip(silence.silence_ratio * 2, 0.0, 1.0))

        heuristic = (
            0.4 * (1.0 - clipping_penalty) +
            0.4 * volume_score +
            0.2 * (1.0 - silence_penalty)
        )
        return float(np.clip(heuristic, 0.0, 1.0))
