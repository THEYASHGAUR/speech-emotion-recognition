"""
Batch status, results, export, and history API routes.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.routes.auth import get_current_user
from app.schemas.models import BatchListItem, BatchResponse, BatchStatus, FileStatus

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)


def _get_batch(request: Request, batch_id: str) -> dict:
    """Helper: fetch a batch from the store or raise 404."""
    batch = request.app.state.batch_store.get(batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch '{batch_id}' not found.",
        )
    return batch


@router.get(
    "/batch/{batch_id}",
    response_model=BatchResponse,
    summary="Get batch status and results",
)
async def get_batch(
    batch_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> BatchResponse:
    """Poll batch status. Results populate as files complete."""
    get_current_user(credentials)
    batch = _get_batch(request, batch_id)

    return BatchResponse(
        batch_id=batch["batch_id"],
        status=batch["status"],
        created_at=batch["created_at"],
        updated_at=batch["updated_at"],
        total_files=batch["total_files"],
        completed_files=batch["completed_files"],
        failed_files=batch["failed_files"],
        results=batch.get("results", []),
        summary=batch.get("summary"),
        validation_errors=batch.get("validation_errors", []),
    )


@router.get(
    "/batch/{batch_id}/export",
    summary="Export batch results as CSV",
    response_class=StreamingResponse,
)
async def export_batch_csv(
    batch_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> StreamingResponse:
    """
    Export all file results as a downloadable CSV.
    CSV columns match the output JSON schema exactly.
    """
    get_current_user(credentials)
    batch = _get_batch(request, batch_id)

    if batch["status"] == BatchStatus.processing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Batch is still processing. Wait until completed before exporting.",
        )

    results = batch.get("results", [])

    output = io.StringIO()
    fieldnames = [
        "filename",
        "status",
        "emotional_tone",
        "emotional_intensity",
        "background_noise_present",
        "background_noise_type",
        "background_noise_severity",
        "audio_quality",
        "speaker_overlap_present",
        "long_silence_present",
        "confidence",
        "processing_time_seconds",
        "audio_duration_seconds",
        "error_message",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for result in results:
        row = {
            "filename": result.filename,
            "status": result.status.value,
            "processing_time_seconds": result.processing_time_seconds,
            "audio_duration_seconds": result.audio_duration_seconds,
            "error_message": result.error_message or "",
        }

        if result.analysis:
            a = result.analysis
            row.update({
                "emotional_tone": a.emotional_tone.value,
                "emotional_intensity": a.emotional_intensity.value,
                "background_noise_present": a.background_noise_present,
                "background_noise_type": a.background_noise_type.value,
                "background_noise_severity": a.background_noise_severity.value,
                "audio_quality": a.audio_quality.value,
                "speaker_overlap_present": a.speaker_overlap_present,
                "long_silence_present": a.long_silence_present,
                "confidence": a.confidence,
            })
        else:
            for f in fieldnames[2:11]:
                row[f] = ""

        writer.writerow(row)

    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"autoace_results_{batch_id[:8]}_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/batches",
    response_model=List[BatchListItem],
    summary="List all batch jobs",
)
async def list_batches(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> List[BatchListItem]:
    """Return a list of all batch jobs, sorted by creation time (newest first)."""
    get_current_user(credentials)

    items = []
    for batch_id, batch in request.app.state.batch_store.items():
        # Skip internal keys
        if not isinstance(batch, dict) or "status" not in batch:
            continue
        items.append(
            BatchListItem(
                batch_id=batch["batch_id"],
                status=batch["status"],
                created_at=batch["created_at"],
                updated_at=batch["updated_at"],
                total_files=batch["total_files"],
                completed_files=batch["completed_files"],
                failed_files=batch["failed_files"],
            )
        )

    return sorted(items, key=lambda x: x.created_at, reverse=True)
