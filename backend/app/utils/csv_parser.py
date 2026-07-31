"""
CSV parsing and validation utilities for batch label files.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# Required columns in labels.csv (case-insensitive matching)
REQUIRED_COLUMNS = {"filename"}


class CSVValidationError(Exception):
    """Raised when labels.csv is malformed or fails validation."""


def parse_labels_csv(
    csv_content: bytes,
    audio_filenames: Set[str],
) -> Tuple[Dict[str, dict], List[str]]:
    """
    Parse and validate labels.csv content.

    Args:
        csv_content: Raw bytes of the CSV file.
        audio_filenames: Set of audio filenames present in the batch.

    Returns:
        Tuple of:
        - dict mapping filename → row dict
        - list of validation warning messages

    Raises:
        CSVValidationError: If the CSV is unparseable or missing required columns.
    """
    warnings: List[str] = []

    # ── Parse ──────────────────────────────────────────────────────────────
    try:
        df = pd.read_csv(io.BytesIO(csv_content))
    except Exception as exc:
        raise CSVValidationError(f"Cannot parse CSV: {exc}") from exc

    if df.empty:
        raise CSVValidationError("labels.csv is empty.")

    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()

    # ── Required columns ───────────────────────────────────────────────────
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        raise CSVValidationError(
            f"labels.csv is missing required columns: {', '.join(sorted(missing_cols))}"
        )

    # ── Duplicate filenames ────────────────────────────────────────────────
    duplicates = df[df["filename"].duplicated()]["filename"].tolist()
    if duplicates:
        raise CSVValidationError(
            f"Duplicate filenames in labels.csv: {', '.join(duplicates)}"
        )

    # ── Strip whitespace ───────────────────────────────────────────────────
    df["filename"] = df["filename"].str.strip()

    label_map: Dict[str, dict] = {}
    for _, row in df.iterrows():
        label_map[row["filename"]] = row.to_dict()

    # ── Cross-validation ───────────────────────────────────────────────────
    csv_names = set(label_map.keys())

    csv_only = csv_names - audio_filenames
    audio_only = audio_filenames - csv_names

    if csv_only:
        warnings.append(
            f"Files in CSV but not in batch: {', '.join(sorted(csv_only))}"
        )
    if audio_only:
        warnings.append(
            f"Audio files not in CSV (will be processed without labels): "
            f"{', '.join(sorted(audio_only))}"
        )

    logger.info(
        f"CSV parsed: {len(label_map)} label rows, "
        f"{len(audio_filenames)} audio files, {len(warnings)} warnings"
    )

    return label_map, warnings


def validate_batch_filenames(filenames: List[str]) -> List[str]:
    """
    Validate a list of filenames for common issues.
    Returns list of error messages (empty if all valid).
    """
    errors: List[str] = []
    seen: Set[str] = set()

    for name in filenames:
        if name in seen:
            errors.append(f"Duplicate filename: {name}")
        seen.add(name)

        if not name.strip():
            errors.append("Empty filename detected.")

        if len(name) > 255:
            errors.append(f"Filename too long (>255 chars): {name[:50]}...")

    return errors
