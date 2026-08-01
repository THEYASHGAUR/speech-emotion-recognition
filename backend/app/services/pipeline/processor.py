"""
Batch Processing Pipeline.

Orchestrates the full ML analysis pipeline for every audio file in a batch.
Each file is processed independently:
  - One failed file does NOT stop the batch
  - CPU-bound ML work runs in a ThreadPoolExecutor
  - Progress is tracked in the shared batch store

Pipeline per file:
  Load → Normalize → Resample → Emotion → Noise → Quality → Silence → Overlap → Confidence → Result
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import Settings
from app.schemas.models import (
    AudioAnalysis,
    BatchStatus,
    FileResult,
    FileStatus,
)
from app.services.confidence.calculator import ConfidenceCalculator
from app.services.emotion.recognizer import EmotionRecognizer
from app.services.noise.detector import NoiseDetector
from app.services.overlap.detector import OverlapDetector
from app.services.quality.analyzer import QualityAnalyzer
from app.services.silence.detector import SilenceDetector
from app.utils.audio import AudioLoadError, AudioProcessor

logger = logging.getLogger(__name__)


class PipelineProcessor:
    """
    Orchestrates batch audio analysis. All services are injected at construction
    time (loaded once at startup) and reused for all files.
    """

    def __init__(
        self,
        settings: Settings,
        emotion_recognizer: Optional[EmotionRecognizer],
        noise_detector: NoiseDetector,
        quality_analyzer: QualityAnalyzer,
        silence_detector: SilenceDetector,
        overlap_detector: OverlapDetector,
    ) -> None:
        self.settings = settings
        self.emotion_recognizer = emotion_recognizer
        self.noise_detector = noise_detector
        self.quality_analyzer = quality_analyzer
        self.silence_detector = silence_detector
        self.overlap_detector = overlap_detector
        self.audio_processor = AudioProcessor(settings)
        self.confidence_calculator = ConfidenceCalculator(settings)

    async def process_batch(
        self,
        batch_id: str,
        file_paths: List[Path],
        batch_store: Dict[str, Any],
    ) -> None:
        """
        Process a full batch asynchronously.
        Updates batch_store in-place with progress and results.
        """
        logger.info(f"Batch {batch_id}: starting processing of {len(file_paths)} files")

        loop = asyncio.get_running_loop()
        max_workers = self.settings.max_concurrent_files

        batch_store[batch_id]["status"] = BatchStatus.processing
        batch_store[batch_id]["updated_at"] = datetime.now(timezone.utc)

        results: List[FileResult] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            tasks = [
                (fp, loop.run_in_executor(executor, self._process_file_sync, fp))
                for fp in file_paths
            ]

            for fp, future in tasks:
                try:
                    result = await asyncio.wait_for(
                        future,
                        timeout=float(self.settings.processing_timeout_seconds),
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Processing timeout for {fp.name}")
                    result = FileResult(
                        filename=fp.name,
                        status=FileStatus.failed,
                        error_message="Processing timed out.",
                    )
                except Exception as exc:
                    logger.error(f"Unexpected error for {fp.name}: {exc}", exc_info=True)
                    result = FileResult(
                        filename=fp.name,
                        status=FileStatus.failed,
                        error_message=str(exc),
                    )

                results.append(result)

                # Update progress in batch store
                completed = sum(1 for r in results if r.status == FileStatus.completed)
                failed = sum(1 for r in results if r.status == FileStatus.failed)
                batch_store[batch_id].update({
                    "results": results,
                    "completed_files": completed,
                    "failed_files": failed,
                    "updated_at": datetime.now(timezone.utc),
                })

                logger.info(
                    f"Batch {batch_id}: {len(results)}/{len(file_paths)} done "
                    f"({completed} ok, {failed} failed)"
                )

        # Final status
        total = len(file_paths)
        completed = sum(1 for r in results if r.status == FileStatus.completed)
        failed = sum(1 for r in results if r.status == FileStatus.failed)

        if failed == total:
            final_status = BatchStatus.failed
        elif failed > 0:
            final_status = BatchStatus.partial
        else:
            final_status = BatchStatus.completed

        summary = self._compute_summary(results, batch_store[batch_id].get("_start_time"))

        batch_store[batch_id].update({
            "status": final_status,
            "results": results,
            "completed_files": completed,
            "failed_files": failed,
            "summary": summary,
            "updated_at": datetime.now(timezone.utc),
        })

        logger.info(
            f"Batch {batch_id} complete: status={final_status}, "
            f"{completed}/{total} files succeeded"
        )

    def _process_file_sync(self, file_path: Path) -> FileResult:
        """
        Synchronous per-file processing pipeline.
        Runs in a thread pool.

        Returns FileResult — never raises exceptions (errors are captured).
        """
        start = time.perf_counter()
        filename = file_path.name

        try:
            logger.info(f"Processing: {filename}")

            # ── Step 1: Load + preprocess audio ──────────────────────────────
            t0 = time.perf_counter()
            waveform, sr, duration = self.audio_processor.preprocess(file_path)
            logger.info(f"  [{filename}] Step 1 — Load/preprocess: {time.perf_counter() - t0:.2f}s (duration={duration:.1f}s)")

            if self.audio_processor.is_silent(waveform, threshold_db=-70.0):
                return FileResult(
                    filename=filename,
                    status=FileStatus.failed,
                    error_message="Audio file contains only silence.",
                )

            # ── Step 2: Emotion recognition ───────────────────────────────────
            t0 = time.perf_counter()
            tone, intensity, model_conf = (
                self.emotion_recognizer.predict(waveform, sr)
                if self.emotion_recognizer
                else (
                    __import__("app.schemas.models", fromlist=["EmotionalTone"]).EmotionalTone.neutral,
                    __import__("app.schemas.models", fromlist=["EmotionalIntensity"]).EmotionalIntensity.low,
                    0.3,
                )
            )
            logger.info(f"  [{filename}] Step 2 — Emotion: {time.perf_counter() - t0:.2f}s")

            # ── Step 3: Noise detection ───────────────────────────────────────
            t0 = time.perf_counter()
            noise_result = self.noise_detector.analyze(waveform, sr)
            logger.info(f"  [{filename}] Step 3 — Noise: {time.perf_counter() - t0:.2f}s")

            # ── Step 4: Quality analysis ──────────────────────────────────────
            t0 = time.perf_counter()
            quality, quality_features = self.quality_analyzer.analyze(waveform, sr)
            logger.info(f"  [{filename}] Step 4 — Quality: {time.perf_counter() - t0:.2f}s")

            # ── Step 5: Silence detection ─────────────────────────────────────
            t0 = time.perf_counter()
            silence_result = self.silence_detector.analyze(waveform, sr)
            logger.info(f"  [{filename}] Step 5 — Silence: {time.perf_counter() - t0:.2f}s")

            # ── Step 6: Overlap detection ─────────────────────────────────────
            t0 = time.perf_counter()
            overlap_result = self.overlap_detector.analyze(waveform, sr)
            logger.info(f"  [{filename}] Step 6 — Overlap: {time.perf_counter() - t0:.2f}s")

            # ── Step 7: Confidence score ──────────────────────────────────────
            t0 = time.perf_counter()
            confidence = self.confidence_calculator.compute(
                model_confidence=model_conf,
                audio_duration_seconds=duration,
                quality_features=quality_features,
                noise_result=noise_result,
                overlap_result=overlap_result,
                silence_result=silence_result,
            )
            logger.info(f"  [{filename}] Step 7 — Confidence: {time.perf_counter() - t0:.2f}s")

            # ── Assemble result ───────────────────────────────────────────────
            analysis = AudioAnalysis(
                emotional_tone=tone,
                emotional_intensity=intensity,
                background_noise_present=noise_result.background_noise_present,
                background_noise_type=noise_result.background_noise_type,
                background_noise_severity=noise_result.background_noise_severity,
                audio_quality=quality,
                speaker_overlap_present=overlap_result.speaker_overlap_present,
                long_silence_present=silence_result.long_silence_present,
                confidence=confidence,
            )

            processing_time = time.perf_counter() - start
            logger.info(f"Completed {filename} in {processing_time:.2f}s")

            return FileResult(
                filename=filename,
                status=FileStatus.completed,
                analysis=analysis,
                processing_time_seconds=round(processing_time, 3),
                audio_duration_seconds=round(duration, 3),
            )

        except AudioLoadError as exc:
            logger.warning(f"Audio load error for {filename}: {exc}")
            return FileResult(
                filename=filename,
                status=FileStatus.failed,
                error_message=f"Audio error: {exc}",
                processing_time_seconds=round(time.perf_counter() - start, 3),
            )
        except Exception as exc:
            logger.error(f"Pipeline error for {filename}: {exc}", exc_info=True)
            return FileResult(
                filename=filename,
                status=FileStatus.failed,
                error_message=f"Processing failed: {exc}",
                processing_time_seconds=round(time.perf_counter() - start, 3),
            )

    def _compute_summary(
        self, results: List[FileResult], start_time: Optional[float]
    ) -> dict:
        """Compute batch-level summary statistics."""
        completed = [r for r in results if r.status == FileStatus.completed and r.analysis]

        emotion_dist: Dict[str, int] = {}
        quality_dist: Dict[str, int] = {}
        confidences = []

        for r in completed:
            if r.analysis:
                tone = r.analysis.emotional_tone.value
                emotion_dist[tone] = emotion_dist.get(tone, 0) + 1

                qual = r.analysis.audio_quality.value
                quality_dist[qual] = quality_dist.get(qual, 0) + 1

                confidences.append(r.analysis.confidence)

        processing_time = (time.perf_counter() - start_time) if start_time else None

        return {
            "total_files": len(results),
            "completed_files": len(completed),
            "failed_files": len(results) - len(completed),
            "avg_confidence": round(float(sum(confidences) / len(confidences)), 4) if confidences else None,
            "emotion_distribution": emotion_dist,
            "quality_distribution": quality_dist,
            "processing_time_seconds": round(processing_time, 2) if processing_time else None,
        }
