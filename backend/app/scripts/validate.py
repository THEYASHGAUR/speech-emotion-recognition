"""
Validation script to generate confusion matrix and classification report.
Compare predictions against labels.csv ground truth.

Usage:
    python -m app.scripts.validate --labels labels.csv --results results.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    accuracy_score,
)
import numpy as np


def run_validation(labels_path: str, results_path: str) -> None:
    labels_df = pd.read_csv(labels_path)
    results_df = pd.read_csv(results_path)

    # Normalize column names
    labels_df.columns = labels_df.columns.str.strip().str.lower()
    results_df.columns = results_df.columns.str.strip().str.lower()

    # Merge on filename
    merged = pd.merge(labels_df, results_df, on="filename", suffixes=("_true", "_pred"))

    if merged.empty:
        print("ERROR: No matching filenames between labels and results.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"AutoAce AI — Validation Report")
    print(f"{'='*60}")
    print(f"Total matched files: {len(merged)}")

    # Emotion evaluation
    if "emotional_tone_true" in merged.columns and "emotional_tone_pred" in merged.columns:
        y_true = merged["emotional_tone_true"].fillna("neutral")
        y_pred = merged["emotional_tone_pred"].fillna("neutral")

        print(f"\n── Emotional Tone ──────────────────────────────────────")
        print(f"Accuracy: {accuracy_score(y_true, y_pred):.4f}")
        print(f"Macro F1: {f1_score(y_true, y_pred, average='macro', zero_division=0):.4f}")
        print(f"\nClassification Report:")
        print(classification_report(y_true, y_pred, zero_division=0))
        print(f"Confusion Matrix:")
        labels = sorted(set(y_true) | set(y_pred))
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        cm_df = pd.DataFrame(cm, index=labels, columns=labels)
        print(cm_df.to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoAce Validation")
    parser.add_argument("--labels", required=True, help="Path to labels CSV")
    parser.add_argument("--results", required=True, help="Path to exported results CSV")
    args = parser.parse_args()
    run_validation(args.labels, args.results)
