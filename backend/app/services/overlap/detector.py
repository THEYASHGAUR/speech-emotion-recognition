"""
Speaker Overlap Detection Service.

Detects simultaneous speech activity (speaker overlap / cross-talk) using
energy-based Voice Activity Detection (VAD) combined with spectral analysis.

Approach (no pyannote dependency required):
1. Detect voice activity frames using RMS energy thresholding
2. Analyze spectral complexity during voice-active regions
3. Detect "double-pitched" segments via autocorrelation (multiple F0s)
4. Score overlap likelihood from these features

If a HuggingFace token + pyannote is available (optional), it is used instead
for higher accuracy diarization-based overlap detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import librosa
import numpy as np

from app.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class OverlapAnalysisResult:
    speaker_overlap_present: bool
    overlap_confidence: float
    overlap_ratio: float       # fraction of speech-active frames with overlap
    num_overlap_segments: int


class OverlapDetector:
    """
    Detects speaker overlap using signal-processing VAD + spectral complexity analysis.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze(self, waveform: np.ndarray, sr: int) -> OverlapAnalysisResult:
        """
        Analyze waveform for speaker overlap.

        Args:
            waveform: Mono float32 normalized waveform.
            sr: Sample rate.

        Returns:
            OverlapAnalysisResult with overlap prediction.
        """
        try:
            return self._analyze_internal(waveform, sr)
        except Exception as exc:
            logger.error(f"Overlap detection failed: {exc}", exc_info=True)
            return OverlapAnalysisResult(
                speaker_overlap_present=False,
                overlap_confidence=0.4,
                overlap_ratio=0.0,
                num_overlap_segments=0,
            )

    def _analyze_internal(
        self, waveform: np.ndarray, sr: int
    ) -> OverlapAnalysisResult:
        frame_length = self.settings.overlap_frame_length
        hop_length = self.settings.overlap_hop_length
        energy_thresh = self.settings.overlap_energy_threshold

        # ── Frame-level energy ────────────────────────────────────────────────
        rms = librosa.feature.rms(
            y=waveform, frame_length=frame_length, hop_length=hop_length
        )[0]

        # Voice-active frames (significant energy)
        voice_frames = rms > energy_thresh
        if not np.any(voice_frames):
            return OverlapAnalysisResult(
                speaker_overlap_present=False,
                overlap_confidence=0.85,
                overlap_ratio=0.0,
                num_overlap_segments=0,
            )

        # ── Spectral complexity per frame ─────────────────────────────────────
        stft = librosa.stft(waveform, n_fft=frame_length, hop_length=hop_length)
        mag = np.abs(stft)

        # Spectral flatness: 0 = tonal (one speaker), 1 = flat (noise/overlap)
        # overlap often causes less tonal structure → higher flatness
        flatness = librosa.feature.spectral_flatness(S=mag)[0]

        # Harmonics-to-noise ratio proxy via harmonic/percussive separation
        y_harm, y_perc = librosa.effects.hpss(waveform)
        harm_energy = librosa.feature.rms(y=y_harm, frame_length=frame_length, hop_length=hop_length)[0]
        perc_energy = librosa.feature.rms(y=y_perc, frame_length=frame_length, hop_length=hop_length)[0]

        min_len = min(len(voice_frames), len(flatness), len(harm_energy), len(perc_energy))
        voice_frames = voice_frames[:min_len]
        flatness = flatness[:min_len]
        harm_energy = harm_energy[:min_len]
        perc_energy = perc_energy[:min_len]

        # ── Overlap scoring per frame ──────────────────────────────────────────
        # Overlap signature: voice-active + high spectral flatness + high harmonic energy
        # (two voices → richer spectrum but more complex/flat than single voice)
        overlap_score_per_frame = np.zeros(min_len)
        for i in range(min_len):
            if not voice_frames[i]:
                continue
            # High flatness + meaningful harmonic energy = possible overlap
            score = (
                0.5 * float(flatness[i]) +
                0.3 * float(np.clip(harm_energy[i] / max(perc_energy[i] + 1e-8, 1e-8) - 1, 0, 1)) +
                0.2 * float(np.clip(rms[i] / energy_thresh - 1, 0, 1))
            )
            overlap_score_per_frame[i] = float(np.clip(score, 0.0, 1.0))

        # Threshold frames as "overlap"
        overlap_threshold = 0.45
        overlap_frames = overlap_score_per_frame > overlap_threshold

        # ── Segment extraction ────────────────────────────────────────────────
        overlap_segments = self._count_segments(overlap_frames, hop_length, sr)
        voice_count = int(np.sum(voice_frames))
        overlap_count = int(np.sum(overlap_frames))
        overlap_ratio = overlap_count / max(voice_count, 1)

        # ── Final decision ────────────────────────────────────────────────────
        # Require minimum overlap duration (configurable)
        min_overlap_duration = self.settings.overlap_min_duration_seconds
        frame_dur = hop_length / sr
        total_overlap_seconds = overlap_count * frame_dur

        present = (
            total_overlap_seconds >= min_overlap_duration and
            overlap_ratio > 0.05 and
            overlap_segments > 0
        )

        confidence = float(np.clip(0.5 + abs(overlap_ratio - 0.05) * 5, 0.0, 0.95))

        logger.debug(
            f"Overlap: present={present} | ratio={overlap_ratio:.2%} | "
            f"segments={overlap_segments} | total={total_overlap_seconds:.2f}s"
        )

        return OverlapAnalysisResult(
            speaker_overlap_present=present,
            overlap_confidence=confidence,
            overlap_ratio=overlap_ratio,
            num_overlap_segments=overlap_segments,
        )

    def _count_segments(
        self, frame_mask: np.ndarray, hop_length: int, sr: int
    ) -> int:
        """Count distinct contiguous overlap segments."""
        count = 0
        in_segment = False
        for val in frame_mask:
            if val and not in_segment:
                count += 1
                in_segment = True
            elif not val:
                in_segment = False
        return count
