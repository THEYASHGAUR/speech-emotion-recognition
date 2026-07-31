/**
 * Shared utility functions for the frontend.
 */

import {
  AudioQuality,
  BatchStatus,
  EmotionalTone,
  NoiseSeverity,
  EmotionalIntensity,
} from "./api";

// ── Emotion helpers ──────────────────────────────────────────────────────────

export const EMOTION_LABELS: Record<EmotionalTone, string> = {
  neutral: "Neutral",
  satisfied: "Satisfied",
  frustrated: "Frustrated",
  upset: "Upset",
  distressed: "Distressed",
};

export const EMOTION_COLORS: Record<EmotionalTone, string> = {
  neutral: "bg-slate-100 text-slate-700 border-slate-200",
  satisfied: "bg-emerald-50 text-emerald-700 border-emerald-200",
  frustrated: "bg-orange-50 text-orange-700 border-orange-200",
  upset: "bg-amber-50 text-amber-700 border-amber-200",
  distressed: "bg-red-50 text-red-700 border-red-200",
};

export const EMOTION_EMOJI: Record<EmotionalTone, string> = {
  neutral: "😐",
  satisfied: "😊",
  frustrated: "😤",
  upset: "😟",
  distressed: "😰",
};

// ── Quality helpers ──────────────────────────────────────────────────────────

export const QUALITY_LABELS: Record<AudioQuality, string> = {
  clear: "Clear",
  slightly_impaired: "Slightly Impaired",
  severely_impaired: "Severely Impaired",
};

export const QUALITY_COLORS: Record<AudioQuality, string> = {
  clear: "bg-emerald-50 text-emerald-700 border-emerald-200",
  slightly_impaired: "bg-amber-50 text-amber-700 border-amber-200",
  severely_impaired: "bg-red-50 text-red-700 border-red-200",
};

// ── Batch status helpers ─────────────────────────────────────────────────────

export const STATUS_LABELS: Record<BatchStatus, string> = {
  uploading: "Uploading",
  validating: "Validating",
  processing: "Processing",
  completed: "Completed",
  partial: "Partial",
  failed: "Failed",
};

export const STATUS_COLORS: Record<BatchStatus, string> = {
  uploading: "bg-blue-50 text-blue-700 border-blue-200",
  validating: "bg-purple-50 text-purple-700 border-purple-200",
  processing: "bg-amber-50 text-amber-700 border-amber-200",
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  partial: "bg-orange-50 text-orange-700 border-orange-200",
  failed: "bg-red-50 text-red-700 border-red-200",
};

// ── Confidence helpers ───────────────────────────────────────────────────────

export function confidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "text-emerald-600";
  if (confidence >= 0.6) return "text-amber-600";
  return "text-red-600";
}

export function confidenceLabel(confidence: number): string {
  if (confidence >= 0.8) return "High";
  if (confidence >= 0.6) return "Medium";
  return "Low";
}

// ── Formatting ───────────────────────────────────────────────────────────────

export function formatDuration(seconds?: number): string {
  if (!seconds) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s}s`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export const INTENSITY_LABELS: Record<EmotionalIntensity, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

export const INTENSITY_COLORS: Record<EmotionalIntensity, string> = {
  low: "bg-slate-100 text-slate-700 border-slate-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  high: "bg-red-50 text-red-700 border-red-200",
};
