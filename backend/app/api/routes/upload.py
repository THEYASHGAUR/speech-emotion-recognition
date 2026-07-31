"""
Upload API route.

Accepts:
- A ZIP file containing audio files + labels.csv
- OR individual audio files uploaded as multipart/form-data

Validates:
- File formats
- CSV validity
- Duplicate filenames
- Missing files

On success, queues the batch for background processing and returns a batch_id.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import shutil
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.routes.auth import get_current_user
from app.config import get_settings
from app.schemas.models import BatchStatus, FileStatus, UploadResponse
from app.services.pipeline.processor import PipelineProcessor
from app.utils.audio import AudioProcessor
from app.utils.csv_parser import CSVValidationError, parse_labels_csv, validate_batch_filenames

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a batch of audio files for analysis",
)
async def upload_batch(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Audio files or a single ZIP archive"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UploadResponse:
    """
    Upload audio files for batch processing.

    Accepts:
    - A single ZIP file (containing audio files + optional labels.csv)
    - Multiple audio files directly

    Returns a `batch_id` that can be polled for status and results.
    """
    username = get_current_user(credentials)

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded.",
        )

    batch_id = str(uuid.uuid4())
    batch_dir = Path(settings.upload_dir) / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    validation_errors: List[str] = []
    audio_files: List[Path] = []
    labels_csv_content: Optional[bytes] = None
    audio_processor = AudioProcessor(settings)

    try:
        # ── Handle ZIP upload ─────────────────────────────────────────────────
        if len(files) == 1 and files[0].filename.lower().endswith(".zip"):
            zip_file = files[0]
            content = await zip_file.read()

            if len(content) > settings.max_upload_size_mb * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Upload exceeds maximum size of {settings.max_upload_size_mb}MB.",
                )

            audio_files, labels_csv_content, zip_errors = await _extract_zip(
                content, batch_dir, audio_processor
            )
            validation_errors.extend(zip_errors)

        # ── Handle direct file upload ─────────────────────────────────────────
        else:
            for upload in files:
                if not upload.filename:
                    continue

                content = await upload.read()

                if upload.filename.lower() == "labels.csv":
                    labels_csv_content = content
                    continue

                ext = Path(upload.filename).suffix.lower()
                allowed = [e.lower() for e in settings.allowed_audio_extensions]

                if ext not in allowed:
                    validation_errors.append(
                        f"Unsupported format '{ext}' for file: {upload.filename}"
                    )
                    continue

                dest = batch_dir / upload.filename
                dest.write_bytes(content)
                audio_files.append(dest)

        # ── Filename deduplication ────────────────────────────────────────────
        filenames = [f.name for f in audio_files]
        dup_errors = validate_batch_filenames(filenames)
        validation_errors.extend(dup_errors)

        if not audio_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid audio files found in upload.",
            )

        # ── CSV validation ────────────────────────────────────────────────────
        if labels_csv_content:
            try:
                audio_set = {f.name for f in audio_files}
                _, csv_warnings = parse_labels_csv(labels_csv_content, audio_set)
                validation_errors.extend(csv_warnings)
            except CSVValidationError as exc:
                validation_errors.append(f"labels.csv error: {exc}")

        # ── Initialize batch in store ─────────────────────────────────────────
        now = datetime.now(timezone.utc)
        request.app.state.batch_store[batch_id] = {
            "batch_id": batch_id,
            "status": BatchStatus.processing,
            "created_at": now,
            "updated_at": now,
            "total_files": len(audio_files),
            "completed_files": 0,
            "failed_files": 0,
            "results": [],
            "summary": None,
            "validation_errors": validation_errors,
            "_start_time": time.perf_counter(),
            "_batch_dir": str(batch_dir),
            "username": username,
        }

        # ── Kick off background processing ────────────────────────────────────
        processor = PipelineProcessor(
            settings=settings,
            emotion_recognizer=request.app.state.emotion_recognizer,
            noise_detector=request.app.state.noise_detector,
            quality_analyzer=request.app.state.quality_analyzer,
            silence_detector=request.app.state.silence_detector,
            overlap_detector=request.app.state.overlap_detector,
        )

        background_tasks.add_task(
            processor.process_batch,
            batch_id=batch_id,
            file_paths=audio_files,
            batch_store=request.app.state.batch_store,
        )

        logger.info(
            f"Batch {batch_id} queued: {len(audio_files)} files, "
            f"{len(validation_errors)} validation issues"
        )

        return UploadResponse(
            batch_id=batch_id,
            message=f"Batch accepted. Processing {len(audio_files)} files.",
            total_files=len(audio_files),
            validation_errors=validation_errors,
        )

    except HTTPException:
        # Clean up batch dir on HTTP errors
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(batch_dir, ignore_errors=True)
        logger.error(f"Upload error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload processing failed: {exc}",
        )


async def _extract_zip(
    content: bytes,
    dest_dir: Path,
    audio_processor: AudioProcessor,
) -> tuple[List[Path], Optional[bytes], List[str]]:
    """Extract a ZIP archive, returning audio file paths, CSV content, and errors."""
    errors: List[str] = []
    audio_files: List[Path] = []
    csv_content: Optional[bytes] = None

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for member in zf.namelist():
                # Skip directories and macOS metadata
                if member.endswith("/") or "__MACOSX" in member or member.startswith("."):
                    continue

                basename = Path(member).name
                ext = Path(basename).suffix.lower()

                if basename.lower() == "labels.csv":
                    csv_content = zf.read(member)
                    continue

                allowed = [e.lower() for e in audio_processor.settings.allowed_audio_extensions]
                if ext not in allowed:
                    errors.append(f"Skipping unsupported file in ZIP: {basename}")
                    continue

                dest = dest_dir / basename
                dest.write_bytes(zf.read(member))
                audio_files.append(dest)

    except zipfile.BadZipFile:
        errors.append("Uploaded file is not a valid ZIP archive.")

    return audio_files, csv_content, errors
