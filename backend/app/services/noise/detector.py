"""
Background Noise Detection Service.

Uses a hybrid signal-processing and acoustic feature analysis approach:
1. SNR estimation to determine if noise is present
2. Spectral features (centroid, rolloff, bandwidth, ZCR, MFCC) to classify noise type
3. Multi-band energy analysis to determine severity

No external model is required — all analysis is done with librosa.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import librosa
import numpy as np
import scipy.stats

from app.config import Settings
from app.schemas.models import NoiseType, NoiseSeverity

logger = logging.getLogger(__name__)


@dataclass
class NoiseAnalysisResult:
    background_noise_present: bool
    background_noise_type: NoiseType
    background_noise_severity: NoiseSeverity
    snr_db: float
    feature_confidence: float


class NoiseDetector:
    """
    Hybrid noise detector using signal processing and acoustic feature analysis.
    Classifies noise type based on spectral fingerprint of non-speech segments.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze(self, waveform: np.ndarray, sr: int) -> NoiseAnalysisResult:
        """
        Analyze a waveform for background noise.

        Args:
            waveform: Mono float32 waveform.
            sr: Sample rate.

        Returns:
            NoiseAnalysisResult with all noise predictions.
        """
        try:
            return self._analyze_internal(waveform, sr)
        except Exception as exc:
            logger.error(f"Noise analysis failed: {exc}", exc_info=True)
            return NoiseAnalysisResult(
                background_noise_present=False,
                background_noise_type=NoiseType.none,
                background_noise_severity=NoiseSeverity.none,
                snr_db=30.0,
                feature_confidence=0.4,
            )

    def _analyze_internal(self, waveform: np.ndarray, sr: int) -> NoiseAnalysisResult:
        from app.utils.audio import AudioProcessor
        snr_db = AudioProcessor.compute_snr(waveform, sr)

        noise_present = snr_db < self.settings.noise_snr_threshold_db

        # ── Extract non-speech (noise) segments ──────────────────────────────
        noise_segments = self._extract_noise_segments(waveform, sr)

        if len(noise_segments) == 0 or not noise_present:
            return NoiseAnalysisResult(
                background_noise_present=False,
                background_noise_type=NoiseType.none,
                background_noise_severity=NoiseSeverity.none,
                snr_db=snr_db,
                feature_confidence=0.85,
            )

        # ── Classify noise from concatenated noise segments ───────────────────
        noise_audio = np.concatenate(noise_segments)
        noise_type, type_confidence = self._classify_noise_type(noise_audio, sr)
        severity = self._determine_severity(snr_db)

        return NoiseAnalysisResult(
            background_noise_present=True,
            background_noise_type=noise_type,
            background_noise_severity=severity,
            snr_db=snr_db,
            feature_confidence=type_confidence,
        )

    def _extract_noise_segments(
        self, waveform: np.ndarray, sr: int
    ) -> list:
        """
        Extract segments likely to contain noise (low-energy, non-speech frames).
        Uses RMS energy thresholding.
        """
        frame_length = int(0.025 * sr)
        hop_length = int(0.010 * sr)

        rms = librosa.feature.rms(
            y=waveform, frame_length=frame_length, hop_length=hop_length
        )[0]

        # Frames below 40th percentile energy = likely noise
        threshold = np.percentile(rms, 40)
        noise_frame_indices = np.where(rms < threshold)[0]

        segments = []
        for idx in noise_frame_indices:
            start = idx * hop_length
            end = min(start + frame_length, len(waveform))
            if end > start:
                segments.append(waveform[start:end])

        return segments

    def _classify_noise_type(
        self, noise_audio: np.ndarray, sr: int
    ) -> Tuple[NoiseType, float]:
        """
        Classify noise type using spectral and temporal features.

        Feature set:
        - Spectral centroid (brightness)
        - Spectral rolloff (high-frequency content)
        - Spectral bandwidth (spread)
        - Zero crossing rate (tonality vs. noise)
        - MFCC delta (temporal variation)
        - Spectral flux (transient content)
        """
        if len(noise_audio) < sr * 0.1:  # Need at least 100ms
            return NoiseType.none, 0.4

        # Feature extraction
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=noise_audio, sr=sr)))
        rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=noise_audio, sr=sr, roll_percent=0.85)))
        bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=noise_audio, sr=sr)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y=noise_audio)))
        mfccs = librosa.feature.mfcc(y=noise_audio, sr=sr, n_mfcc=13)
        mfcc_var = float(np.mean(np.var(mfccs, axis=1)))

        # Tempo and periodicity — use at most 5s to avoid slow beat_track on CPU
        try:
            beat_segment = noise_audio[:min(len(noise_audio), sr * 5)]
            tempo, _ = librosa.beat.beat_track(y=beat_segment, sr=sr)
            has_rhythm = float(tempo) > 60 and float(tempo) < 200
        except Exception:
            has_rhythm = False

        # ── Rule-based classifier ─────────────────────────────────────────────
        # Normalize centroid relative to Nyquist
        nyquist = sr / 2
        rel_centroid = centroid / nyquist
        rel_rolloff = rolloff / nyquist

        # Music: high periodicity, high spectral variation, mid centroid
        if has_rhythm and mfcc_var > 100 and 0.15 < rel_centroid < 0.5:
            return NoiseType.music, 0.78

        # Wind: high ZCR, low centroid, broadband
        if zcr > 0.15 and rel_centroid < 0.2 and bandwidth > 2000:
            return NoiseType.wind, 0.74

        # Keyboard: high ZCR, transient, mid-high frequency
        if zcr > 0.1 and rel_centroid > 0.3 and mfcc_var < 80:
            return NoiseType.keyboard, 0.69

        # Television/speech-like: moderate centroid, medium ZCR
        if 0.1 < rel_centroid < 0.35 and 0.03 < zcr < 0.12:
            return NoiseType.television, 0.66

        # Road noise: low centroid, low ZCR, continuous
        if rel_centroid < 0.15 and zcr < 0.05 and bandwidth > 1000:
            return NoiseType.road_noise, 0.71

        # Office chatter: mid centroid, moderate ZCR (speech-like but noisy)
        if 0.1 < rel_centroid < 0.4 and 0.05 < zcr < 0.15:
            return NoiseType.office_chatter, 0.65

        # Mechanical: low centroid, low ZCR, low variation
        if rel_centroid < 0.2 and zcr < 0.08 and mfcc_var < 50:
            return NoiseType.mechanical, 0.67

        return NoiseType.office_chatter, 0.50  # Default fallback

    def _determine_severity(self, snr_db: float) -> NoiseSeverity:
        """Map SNR to noise severity level using configurable thresholds."""
        if snr_db >= self.settings.noise_severity_low_snr:
            return NoiseSeverity.low
        elif snr_db >= self.settings.noise_severity_high_snr:
            return NoiseSeverity.medium
        else:
            return NoiseSeverity.high
