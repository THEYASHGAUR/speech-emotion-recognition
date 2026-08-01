/**
 * AutoAce AI — Axios API client with React Query integration.
 * All API calls go through this module.
 */

import axios, { AxiosError } from "axios";

const rawApiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_BASE = rawApiBase.replace(/\/+$/, "");

export const apiClient = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  timeout: 60_000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach JWT token from localStorage on every request
apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("autoace_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Redirect to login on 401
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("autoace_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ──────────────────────── Auth ─────────────────────────────────────────────

export interface LoginPayload {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", payload);
  return data;
}

// ──────────────────────── Upload ───────────────────────────────────────────

export interface UploadResponse {
  batch_id: string;
  message: string;
  total_files: number;
  validation_errors: string[];
}

export async function uploadBatch(files: File[]): Promise<UploadResponse> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const { data } = await apiClient.post<UploadResponse>("/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120_000,
  });
  return data;
}

// ──────────────────────── Batch ────────────────────────────────────────────

export type BatchStatus =
  | "uploading"
  | "validating"
  | "processing"
  | "completed"
  | "partial"
  | "failed";

export type EmotionalTone =
  | "neutral"
  | "satisfied"
  | "frustrated"
  | "upset"
  | "distressed";

export type EmotionalIntensity = "low" | "medium" | "high";

export type AudioQuality = "clear" | "slightly_impaired" | "severely_impaired";

export type NoiseType =
  | "office_chatter"
  | "road_noise"
  | "music"
  | "wind"
  | "keyboard"
  | "television"
  | "mechanical"
  | "none";

export type NoiseSeverity = "low" | "medium" | "high" | "none";

export interface AudioAnalysis {
  emotional_tone: EmotionalTone;
  emotional_intensity: EmotionalIntensity;
  background_noise_present: boolean;
  background_noise_type: NoiseType;
  background_noise_severity: NoiseSeverity;
  audio_quality: AudioQuality;
  speaker_overlap_present: boolean;
  long_silence_present: boolean;
  confidence: number;
}

export interface FileResult {
  filename: string;
  status: "pending" | "processing" | "completed" | "failed";
  analysis?: AudioAnalysis;
  error_message?: string;
  processing_time_seconds?: number;
  audio_duration_seconds?: number;
}

export interface BatchSummary {
  total_files: number;
  completed_files: number;
  failed_files: number;
  avg_confidence?: number;
  emotion_distribution: Record<string, number>;
  quality_distribution: Record<string, number>;
  processing_time_seconds?: number;
}

export interface BatchResponse {
  batch_id: string;
  status: BatchStatus;
  created_at: string;
  updated_at: string;
  total_files: number;
  completed_files: number;
  failed_files: number;
  results: FileResult[];
  summary?: BatchSummary;
  validation_errors: string[];
}

export interface BatchListItem {
  batch_id: string;
  status: BatchStatus;
  created_at: string;
  updated_at: string;
  total_files: number;
  completed_files: number;
  failed_files: number;
}

export async function getBatch(batchId: string): Promise<BatchResponse> {
  const { data } = await apiClient.get<BatchResponse>(`/batch/${batchId}`);
  return data;
}

export async function getBatches(): Promise<BatchListItem[]> {
  const { data } = await apiClient.get<BatchListItem[]>("/batches");
  return data;
}

export function getBatchExportUrl(batchId: string): string {
  const token = typeof window !== "undefined" ? localStorage.getItem("autoace_token") : "";
  return `${API_BASE}/api/v1/batch/${batchId}/export`;
}

export async function exportBatchCsv(batchId: string): Promise<void> {
  const token = localStorage.getItem("autoace_token");
  const response = await apiClient.get(`/batch/${batchId}/export`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  const disposition = response.headers["content-disposition"] || "";
  const match = disposition.match(/filename="([^"]+)"/);
  link.download = match ? match[1] : `results_${batchId}.csv`;
  link.click();
  window.URL.revokeObjectURL(url);
}
