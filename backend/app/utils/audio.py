"""
Audio loading, normalization, format validation, and preprocessing utilities.
Uses librosa as primary loader with ffmpeg as fallback for unsupported formats.
"""

from __future__ import annotations

import io
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import librosa
import numpy as np
import soundfile as sf

from app.config import Settings

logger = logging.getLogger(__name__)


class AudioLoadError(Exception):
    """Raised when audio cannot be loaded or is invalid."""


class AudioProcessor:
    """
    Handles audio file I/O and preprocessing.
    All methods are pure functions on numpy arrays to keep them testable.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def load(self, file_path: str | Path) -> Tuple[np.ndarray, int]:
        """
        Load an audio file and return (waveform, sample_rate).

        Args:
            file_path: Path to the audio file.

        Returns:
            Tuple of (mono float32 waveform, original sample rate).

        Raises:
            AudioLoadError: If the file cannot be loaded.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise AudioLoadError(f"File not found: {file_path}")

        ext = file_path.suffix.lower()
        allowed = [e.lower() for e in self.settings.allowed_audio_extensions]
        if ext not in allowed:
            raise AudioLoadError(
                f"Unsupported format '{ext}'. Allowed: {', '.join(allowed)}"
            )

        # Try soundfile first (fast C library for wav, ogg, flac)
        try:
            waveform, sr = sf.read(str(file_path), dtype="float32")
            if waveform.ndim > 1:
                waveform = waveform.mean(axis=1)
            logger.debug(f"Loaded {file_path.name} via soundfile: sr={sr}, duration={len(waveform)/sr:.2f}s")
            return waveform, int(sr)
        except Exception:
            pass

        # Fallback to librosa
        try:
            waveform, sr = librosa.load(
                str(file_path),
                sr=None,  # Preserve original sample rate
                mono=True,
            )
            logger.debug(f"Loaded {file_path.name}: sr={sr}, duration={len(waveform)/sr:.2f}s")
            return waveform, int(sr)
        except Exception as e:
            logger.warning(f"librosa failed for {file_path.name}: {e}, trying ffmpeg...")

        # Fallback: convert with ffmpeg to a temporary WAV then reload
        return self._load_via_ffmpeg(file_path)

    def _load_via_ffmpeg(self, file_path: Path) -> Tuple[np.ndarray, int]:
        """Use ffmpeg to convert then load as WAV."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(file_path),
                    "-ar", str(self.settings.target_sample_rate),
                    "-ac", "1", "-f", "wav", tmp_path,
                ],
                capture_output=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise AudioLoadError(
                    f"ffmpeg conversion failed: {result.stderr.decode(errors='replace')}"
                )

            waveform, sr = sf.read(tmp_path, dtype="float32")
            if waveform.ndim > 1:
                waveform = waveform.mean(axis=1)
            return waveform, sr
        except subprocess.TimeoutExpired:
            raise AudioLoadError("ffmpeg conversion timed out")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def normalize(self, waveform: np.ndarray) -> np.ndarray:
        """
        Peak-normalize waveform to [-1, 1].
        Handles silence (all zeros) by returning unchanged.
        """
        peak = np.max(np.abs(waveform))
        if peak < 1e-8:
            return waveform
        return waveform / peak

    def resample(self, waveform: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Resample waveform to target sample rate."""
        if orig_sr == target_sr:
            return waveform
        return librosa.resample(waveform, orig_sr=orig_sr, target_sr=target_sr)

    def preprocess(self, file_path: str | Path) -> Tuple[np.ndarray, int, float]:
        """
        Full preprocessing pipeline:
        1. Load
        2. Normalize
        3. Resample to target_sr if needed

        Returns:
            (preprocessed_waveform, sample_rate, duration_seconds)
        """
        waveform, sr = self.load(file_path)
        duration = len(waveform) / sr

        if duration > self.settings.max_audio_duration_seconds:
            logger.warning(
                f"Audio duration {duration:.1f}s exceeds limit "
                f"{self.settings.max_audio_duration_seconds}s — truncating."
            )
            max_samples = int(self.settings.max_audio_duration_seconds * sr)
            waveform = waveform[:max_samples]
            duration = self.settings.max_audio_duration_seconds

        waveform = self.normalize(waveform)

        if sr != self.settings.target_sample_rate:
            waveform = self.resample(waveform, sr, self.settings.target_sample_rate)
            sr = self.settings.target_sample_rate

        return waveform, sr, duration

    @staticmethod
    def compute_snr(waveform: np.ndarray, sr: int) -> float:
        """
        Estimate signal-to-noise ratio in dB using a simple
        energy-based estimator (voice activity vs. non-voice segments).
        """
        frame_length = int(0.025 * sr)  # 25ms frames
        hop_length = int(0.010 * sr)    # 10ms hop

        rms = librosa.feature.rms(
            y=waveform, frame_length=frame_length, hop_length=hop_length
        )[0]

        if len(rms) == 0 or np.max(rms) < 1e-10:
            return 0.0

        # Voice frames: top 20% energy
        threshold = np.percentile(rms, 80)
        signal_frames = rms[rms >= threshold]
        noise_frames = rms[rms < threshold]

        signal_power = np.mean(signal_frames ** 2) if len(signal_frames) > 0 else 1e-10
        noise_power = np.mean(noise_frames ** 2) if len(noise_frames) > 0 else 1e-10

        if noise_power < 1e-15:
            return 60.0  # Essentially no noise

        snr_db = 10 * np.log10(signal_power / noise_power)
        return float(np.clip(snr_db, -20.0, 60.0))

    @staticmethod
    def is_silent(waveform: np.ndarray, threshold_db: float = -60.0) -> bool:
        """Return True if the entire waveform is below the given dB threshold."""
        rms = np.sqrt(np.mean(waveform ** 2))
        if rms < 1e-10:
            return True
        rms_db = 20 * np.log10(rms)
        return rms_db < threshold_db

    @staticmethod
    def get_extension(filename: str) -> str:
        return Path(filename).suffix.lower()
