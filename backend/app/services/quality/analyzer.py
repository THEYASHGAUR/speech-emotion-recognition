"""
Audio Quality Analysis Service.

Evaluates audio quality by analyzing multiple acoustic dimensions:
- Volume / RMS level
- Signal-to-noise ratio (SNR)
- Clipping detection
- Echo estimation via autocorrelation
- Spectral rolloff (muffling)
- High-frequency energy loss

Returns a 3-class quality label:
  clear | slightly_impaired | severely_impaired
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict

import librosa
import numpy as np

from app.config import Settings
from app.schemas.models import AudioQuality

logger = logging.getLogger(__name__)


@dataclass
class QualityFeatures:
    """Raw quality measurements before classification."""
    rms_db: float = 0.0
    peak_db: float = 0.0
    snr_db: float = 0.0
    clipping_ratio: float = 0.0
    echo_score: float = 0.0       # 0 = no echo, 1 = heavy echo
    muffling_score: float = 0.0   # 0 = bright, 1 = muffled
    dynamic_range_db: float = 0.0
    quality_score: float = 1.0    # Aggregate 0-1 score (higher = better)


class QualityAnalyzer:
    """
    Analyzes audio quality using signal processing features.
    No ML model required — all analysis is interpretable and deterministic.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze(self, waveform: np.ndarray, sr: int) -> tuple[AudioQuality, QualityFeatures]:
        """
        Analyze audio quality.

        Args:
            waveform: Mono float32 waveform (normalized).
            sr: Sample rate.

        Returns:
            Tuple of (AudioQuality label, QualityFeatures breakdown).
        """
        try:
            return self._analyze_internal(waveform, sr)
        except Exception as exc:
            logger.error(f"Quality analysis failed: {exc}", exc_info=True)
            features = QualityFeatures(quality_score=0.5)
            return AudioQuality.slightly_impaired, features

    def _analyze_internal(
        self, waveform: np.ndarray, sr: int
    ) -> tuple[AudioQuality, QualityFeatures]:
        from app.utils.audio import AudioProcessor

        features = QualityFeatures()

        # ── Volume ──────────────────────────────────────────────────────────
        rms = float(np.sqrt(np.mean(waveform ** 2)))
        peak = float(np.max(np.abs(waveform)))
        features.rms_db = 20 * np.log10(max(rms, 1e-10))
        features.peak_db = 20 * np.log10(max(peak, 1e-10))
        features.dynamic_range_db = features.peak_db - features.rms_db

        # ── SNR ──────────────────────────────────────────────────────────────
        features.snr_db = AudioProcessor.compute_snr(waveform, sr)

        # ── Clipping ─────────────────────────────────────────────────────────
        clip_thresh = self.settings.quality_clipping_threshold
        clipped_samples = np.sum(np.abs(waveform) >= clip_thresh)
        features.clipping_ratio = clipped_samples / max(len(waveform), 1)

        # ── Echo (autocorrelation lag analysis) ──────────────────────────────
        features.echo_score = self._estimate_echo(waveform, sr)

        # ── Muffling (spectral rolloff) ───────────────────────────────────────
        features.muffling_score = self._estimate_muffling(waveform, sr)

        # ── Aggregate quality score (0 = worst, 1 = best) ───────────────────
        quality_score = self._compute_quality_score(features)
        features.quality_score = quality_score

        # ── Classify ──────────────────────────────────────────────────────────
        quality = self._classify_quality(quality_score, features)

        logger.debug(
            f"Quality: {quality} | SNR={features.snr_db:.1f}dB | "
            f"Clipping={features.clipping_ratio:.4f} | "
            f"Echo={features.echo_score:.2f} | Muffling={features.muffling_score:.2f}"
        )

        return quality, features

    def _estimate_echo(self, waveform: np.ndarray, sr: int) -> float:
        """
        Estimate echo presence using short-lag autocorrelation.
        Returns score 0.0 (no echo) to 1.0 (heavy echo).
        """
        # Check lags from 20ms to 500ms for significant peaks
        min_lag = int(0.020 * sr)
        max_lag = int(0.500 * sr)

        if len(waveform) < max_lag * 2:
            return 0.0

        # Sample from middle of audio
        start = len(waveform) // 4
        segment = waveform[start : start + sr]  # 1 second segment

        import scipy.signal
        # Fast FFT-based normalized autocorrelation
        corr = scipy.signal.correlate(segment, segment, mode="full", method="fft")
        corr = corr[len(corr) // 2:]
        if corr[0] > 0:
            corr = corr / corr[0]

        lag_range = corr[min_lag:max_lag]
        if len(lag_range) == 0:
            return 0.0

        echo_score = float(np.max(np.abs(lag_range)))
        return float(np.clip(echo_score, 0.0, 1.0))

    def _estimate_muffling(self, waveform: np.ndarray, sr: int) -> float:
        """
        Estimate muffling/low-pass filtering by measuring high-frequency energy loss.
        Returns score 0.0 (bright/clear) to 1.0 (heavily muffled).
        """
        rolloff = librosa.feature.spectral_rolloff(y=waveform, sr=sr, roll_percent=0.85)
        mean_rolloff = float(np.mean(rolloff))
        nyquist = sr / 2

        # Normalize: 0 = muffled (low rolloff), 1 = bright (high rolloff)
        normalized = mean_rolloff / nyquist
        muffling = 1.0 - float(np.clip(normalized, 0.0, 1.0))
        return muffling

    def _compute_quality_score(self, f: QualityFeatures) -> float:
        """
        Compute a composite quality score [0, 1] from individual features.
        Weights are fixed — all features combined linearly.
        """
        # SNR score: 0 dB → 0.0, 40 dB → 1.0
        snr_score = float(np.clip((f.snr_db + 0) / 40.0, 0.0, 1.0))

        # Clipping penalty: 0 clips → 1.0, 1% clips → 0.0
        clip_score = float(np.clip(1.0 - (f.clipping_ratio / self.settings.quality_clipping_ratio_max), 0.0, 1.0))

        # Echo penalty: 0 echo → 1.0, full echo → 0.0
        echo_score = 1.0 - f.echo_score

        # Muffling penalty: 0 muffling → 1.0, full muffling → 0.0
        muffling_score = 1.0 - f.muffling_score

        # Volume score: penalize very low volume
        volume_score = float(np.clip((f.rms_db + 60) / 60.0, 0.0, 1.0))

        # Weighted aggregate
        composite = (
            0.35 * snr_score +
            0.25 * clip_score +
            0.15 * echo_score +
            0.15 * muffling_score +
            0.10 * volume_score
        )
        return float(np.clip(composite, 0.0, 1.0))

    def _classify_quality(self, quality_score: float, f: QualityFeatures) -> AudioQuality:
        """
        Classify into clear / slightly_impaired / severely_impaired.
        Uses both the aggregate score and hard thresholds for critical failures.
        """
        # Hard overrides for critical issues
        if (
            f.clipping_ratio > self.settings.quality_clipping_ratio_max * 5 or
            f.snr_db < self.settings.quality_snr_impaired_threshold - 5
        ):
            return AudioQuality.severely_impaired

        if quality_score >= 0.72:
            return AudioQuality.clear
        elif quality_score >= 0.45:
            return AudioQuality.slightly_impaired
        else:
            return AudioQuality.severely_impaired
