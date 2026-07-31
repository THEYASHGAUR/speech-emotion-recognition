"""
Long Silence Detection Service.

Uses Voice Activity Detection (VAD) via librosa energy thresholding to
identify and measure silent regions in audio.

The silence threshold and minimum duration are fully configurable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Tuple

import librosa
import numpy as np

from app.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class SilenceSegment:
    start_seconds: float
    end_seconds: float

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass
class SilenceAnalysisResult:
    long_silence_present: bool
    silence_segments: List[SilenceSegment]
    total_silence_seconds: float
    longest_silence_seconds: float
    silence_ratio: float  # 0.0–1.0 proportion of audio that is silent


class SilenceDetector:
    """
    Detects long silence regions using energy-based VAD.
    A "long silence" is a continuous silent region exceeding
    `long_silence_min_duration_seconds` (configurable).
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze(self, waveform: np.ndarray, sr: int) -> SilenceAnalysisResult:
        """
        Detect silence regions in a waveform.

        Args:
            waveform: Mono float32 normalized waveform.
            sr: Sample rate.

        Returns:
            SilenceAnalysisResult with all silence metrics.
        """
        try:
            return self._analyze_internal(waveform, sr)
        except Exception as exc:
            logger.error(f"Silence detection failed: {exc}", exc_info=True)
            return SilenceAnalysisResult(
                long_silence_present=False,
                silence_segments=[],
                total_silence_seconds=0.0,
                longest_silence_seconds=0.0,
                silence_ratio=0.0,
            )

    def _analyze_internal(
        self, waveform: np.ndarray, sr: int
    ) -> SilenceAnalysisResult:
        duration = len(waveform) / sr

        # ── Frame-level energy ────────────────────────────────────────────────
        frame_length = int(0.025 * sr)   # 25ms frames
        hop_length = int(0.010 * sr)     # 10ms hop

        rms = librosa.feature.rms(
            y=waveform, frame_length=frame_length, hop_length=hop_length
        )[0]

        # Convert RMS to dB
        rms_db = 20 * np.log10(np.maximum(rms, 1e-10))

        # ── Threshold ─────────────────────────────────────────────────────────
        threshold_db = self.settings.silence_threshold_db
        is_silent_frame = rms_db < threshold_db

        # ── Segment extraction ────────────────────────────────────────────────
        silence_segments = self._extract_segments(
            is_silent_frame, hop_length, sr, duration
        )

        # ── Filter by minimum duration ────────────────────────────────────────
        min_dur = self.settings.long_silence_min_duration_seconds
        long_silences = [s for s in silence_segments if s.duration_seconds >= min_dur]

        total_silence = sum(s.duration_seconds for s in silence_segments)
        longest_silence = max(
            (s.duration_seconds for s in silence_segments), default=0.0
        )
        silence_ratio = total_silence / max(duration, 1e-6)

        result = SilenceAnalysisResult(
            long_silence_present=len(long_silences) > 0,
            silence_segments=long_silences,
            total_silence_seconds=total_silence,
            longest_silence_seconds=longest_silence,
            silence_ratio=float(silence_ratio),
        )

        logger.debug(
            f"Silence: present={result.long_silence_present} | "
            f"longest={longest_silence:.2f}s | ratio={silence_ratio:.2%}"
        )
        return result

    def _extract_segments(
        self,
        is_silent: np.ndarray,
        hop_length: int,
        sr: int,
        total_duration: float,
    ) -> List[SilenceSegment]:
        """Convert frame-level silence mask to time segments."""
        segments: List[SilenceSegment] = []

        if len(is_silent) == 0:
            return segments

        in_silence = False
        seg_start = 0.0

        for i, silent in enumerate(is_silent):
            t = (i * hop_length) / sr
            if silent and not in_silence:
                seg_start = t
                in_silence = True
            elif not silent and in_silence:
                segments.append(SilenceSegment(start_seconds=seg_start, end_seconds=t))
                in_silence = False

        # Handle silence extending to end of file
        if in_silence:
            segments.append(
                SilenceSegment(start_seconds=seg_start, end_seconds=total_duration)
            )

        return segments
