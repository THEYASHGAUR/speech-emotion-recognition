"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import Sidebar from "@/components/Sidebar";
import { uploadBatch, getBatch, BatchResponse } from "@/lib/api";
import { STATUS_COLORS, STATUS_LABELS } from "@/lib/utils";
import {
  Upload,
  FileAudio,
  X,
  CheckCircle2,
  AlertCircle,
  FolderOpen,
  Zap,
  Info,
} from "lucide-react";

const ALLOWED_EXTENSIONS = [".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".webm", ".opus", ".zip"];

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);

  // Batch progress polling
  const [batchId, setBatchId] = useState<string | null>(null);
  const [batchData, setBatchData] = useState<BatchResponse | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("autoace_token");
    if (!token) router.push("/login");
  }, []);

  // Poll for batch status
  useEffect(() => {
    if (!batchId) return;
    pollRef.current = setInterval(async () => {
      try {
        const data = await getBatch(batchId);
        setBatchData(data);
        if (data.status === "completed" || data.status === "failed" || data.status === "partial") {
          clearInterval(pollRef.current!);
        }
      } catch {
        clearInterval(pollRef.current!);
      }
    }, 2000);
    return () => clearInterval(pollRef.current!);
  }, [batchId]);

  function validateFiles(incoming: File[]): { valid: File[]; errors: string[] } {
    const errors: string[] = [];
    const valid: File[] = [];
    const names = new Set<string>();

    for (const file of incoming) {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        errors.push(`Unsupported format: ${file.name}`);
        continue;
      }
      if (names.has(file.name)) {
        errors.push(`Duplicate filename: ${file.name}`);
        continue;
      }
      names.add(file.name);
      valid.push(file);
    }
    return { valid, errors };
  }

  function addFiles(incoming: File[]) {
    setError("");
    const { valid, errors } = validateFiles(incoming);
    if (errors.length > 0) setError(errors.join(" | "));
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...valid.filter((f) => !existing.has(f.name))];
    });
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(Array.from(e.dataTransfer.files));
  }, []);

  async function handleSubmit() {
    if (files.length === 0) return;
    setUploading(true);
    setError("");
    setValidationWarnings([]);

    try {
      const response = await uploadBatch(files);
      setBatchId(response.batch_id);
      if (response.validation_errors.length > 0) {
        setValidationWarnings(response.validation_errors);
      }
      setFiles([]);
    } catch (err: unknown) {
      const msg =
        axios.isAxiosError(err) && err.response?.data?.detail
          ? err.response.data.detail
          : "Upload failed. Please try again.";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setUploading(false);
    }
  }

  const progress = batchData
    ? Math.round(((batchData.completed_files + batchData.failed_files) / Math.max(batchData.total_files, 1)) * 100)
    : 0;

  // If batch is complete, offer navigation
  const isComplete = batchData?.status === "completed" || batchData?.status === "partial";

  return (
    <div className="gradient-bg" style={{ minHeight: "100vh" }}>
      <Sidebar />
      <main className="main-content">
        <div style={{ maxWidth: "760px" }}>
          {/* Header */}
          <div style={{ marginBottom: "32px" }}>
            <h1 style={{ fontSize: "26px", fontWeight: "700", letterSpacing: "-0.02em", marginBottom: "4px" }}>
              Upload Batch
            </h1>
            <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
              Upload a ZIP archive or individual audio files for analysis
            </p>
          </div>

          {/* Upload zone (hidden if batch started) */}
          {!batchId && (
            <>
              {/* Drop zone */}
              <div
                className={`drop-zone ${dragging ? "dragging" : ""}`}
                id="drop-zone"
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                style={{ marginBottom: "20px" }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".wav,.mp3,.ogg,.flac,.m4a,.aac,.webm,.opus,.zip"
                  style={{ display: "none" }}
                  onChange={(e) => addFiles(Array.from(e.target.files || []))}
                />
                <div
                  style={{
                    width: "56px",
                    height: "56px",
                    background: "#e0e7ff",
                    border: "1px solid #c7d2fe",
                    borderRadius: "14px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 16px",
                  }}
                >
                  <Upload size={24} color="#4338ca" />
                </div>
                <p style={{ fontSize: "16px", fontWeight: "600", marginBottom: "6px", color: "var(--text-primary)" }}>
                  Drop files here or click to browse
                </p>
                <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                  Supports ZIP archive or individual audio files (.wav, .mp3, .flac, .ogg, .m4a, .aac)
                </p>
                <p style={{ color: "var(--text-muted)", fontSize: "12px", marginTop: "6px" }}>
                  Include a <code style={{ color: "#4338ca", background: "#e0e7ff", padding: "1px 6px", borderRadius: "4px", fontWeight: "600" }}>labels.csv</code> for ground-truth validation
                </p>
              </div>

              {/* Info box */}
              <div
                style={{
                  padding: "14px 16px",
                  background: "#e0e7ff",
                  border: "1px solid #c7d2fe",
                  borderRadius: "10px",
                  display: "flex",
                  gap: "10px",
                  marginBottom: "20px",
                  fontSize: "12px",
                  color: "#3730a3",
                  lineHeight: "1.6",
                }}
              >
                <Info size={16} style={{ flexShrink: 0, color: "#4338ca", marginTop: "1px" }} />
                <div>
                  <strong style={{ color: "#1e1b4b" }}>ZIP format:</strong> Place audio files + optional{" "}
                  <code style={{ color: "#4338ca", fontWeight: "600" }}>labels.csv</code> inside a ZIP and upload it.{" "}
                  <strong style={{ color: "#1e1b4b" }}>Direct upload:</strong> Select multiple audio files directly.
                </div>
              </div>

              {/* File list */}
              {files.length > 0 && (
                <div className="glass-card" style={{ marginBottom: "20px", overflow: "hidden" }}>
                  <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "14px", fontWeight: "600" }}>
                      {files.length} file{files.length !== 1 ? "s" : ""} selected
                    </span>
                    <button
                      onClick={() => setFiles([])}
                      style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "12px" }}
                    >
                      Clear all
                    </button>
                  </div>
                  <div style={{ maxHeight: "240px", overflowY: "auto" }}>
                    {files.map((file) => (
                      <div
                        key={file.name}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "12px",
                          padding: "10px 20px",
                          borderBottom: "1px solid #f1f5f9",
                        }}
                      >
                        <FileAudio size={16} style={{ color: "var(--accent)", flexShrink: 0 }} />
                        <span style={{ flex: 1, fontSize: "13px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--text-primary)" }}>
                          {file.name}
                        </span>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)", flexShrink: 0 }}>
                          {(file.size / 1024 / 1024).toFixed(1)} MB
                        </span>
                        <button
                          onClick={() => setFiles((p) => p.filter((f) => f.name !== file.name))}
                          style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
                        >
                          <X size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Error */}
              {error && (
                <div
                  style={{
                    padding: "12px 16px",
                    background: "#fef2f2",
                    border: "1px solid #fecaca",
                    borderRadius: "10px",
                    color: "#dc2626",
                    fontSize: "13px",
                    marginBottom: "16px",
                    display: "flex",
                    gap: "8px",
                    alignItems: "flex-start",
                  }}
                >
                  <AlertCircle size={16} style={{ flexShrink: 0, marginTop: "1px" }} />
                  {error}
                </div>
              )}

              {/* Submit button */}
              <button
                id="start-analysis-btn"
                className="btn-primary"
                onClick={handleSubmit}
                disabled={files.length === 0 || uploading}
                style={{ width: "100%", justifyContent: "center", padding: "14px" }}
              >
                {uploading ? (
                  <>
                    <div className="animate-spin" style={{ width: "16px", height: "16px", border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "white", borderRadius: "50%" }} />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Zap size={16} />
                    Start Analysis ({files.length} file{files.length !== 1 ? "s" : ""})
                  </>
                )}
              </button>
            </>
          )}

          {/* Batch progress */}
          {batchId && batchData && (
            <div className="glass-card animate-fade-in" style={{ padding: "28px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
                <div>
                  <h2 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "4px" }}>Batch Processing</h2>
                  <code style={{ fontSize: "12px", color: "#4338ca", background: "#e0e7ff", padding: "2px 8px", borderRadius: "6px", fontWeight: "600" }}>
                    {batchId}
                  </code>
                </div>
                <span className={`badge ${STATUS_COLORS[batchData.status]}`}>
                  {STATUS_LABELS[batchData.status]}
                </span>
              </div>

              {/* Progress bar */}
              <div style={{ marginBottom: "24px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>
                  <span>{batchData.completed_files + batchData.failed_files} / {batchData.total_files} files</span>
                  <span>{progress}%</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
                </div>
              </div>

              {/* File results */}
              {batchData.results.length > 0 && (
                <div>
                  {batchData.results.slice(0, 8).map((result) => (
                    <div
                      key={result.filename}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        padding: "8px 0",
                        borderBottom: "1px solid #f1f5f9",
                        fontSize: "13px",
                      }}
                    >
                      {result.status === "completed" ? (
                        <CheckCircle2 size={14} style={{ color: "var(--success)", flexShrink: 0 }} />
                      ) : result.status === "failed" ? (
                        <AlertCircle size={14} style={{ color: "var(--danger)", flexShrink: 0 }} />
                      ) : (
                        <div className="animate-spin" style={{ width: "14px", height: "14px", border: "2px solid var(--border)", borderTopColor: "var(--accent)", borderRadius: "50%", flexShrink: 0 }} />
                      )}
                      <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--text-primary)" }}>
                        {result.filename}
                      </span>
                      {result.analysis && (
                        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                          {result.analysis.emotional_tone} • {(result.analysis.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                      {result.error_message && (
                        <span style={{ fontSize: "11px", color: "#dc2626", fontWeight: "500" }}>Error</span>
                      )}
                    </div>
                  ))}
                  {batchData.results.length > 8 && (
                    <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "8px" }}>
                      +{batchData.results.length - 8} more files...
                    </p>
                  )}
                </div>
              )}

              {/* Validation warnings */}
              {validationWarnings.length > 0 && (
                <div style={{ marginTop: "16px", padding: "12px", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "10px" }}>
                  {validationWarnings.map((w, i) => (
                    <p key={i} style={{ fontSize: "12px", color: "#b45309" }}>{w}</p>
                  ))}
                </div>
              )}

              {/* Actions */}
              {isComplete && (
                <div style={{ display: "flex", gap: "12px", marginTop: "24px" }}>
                  <button
                    className="btn-primary"
                    onClick={() => router.push(`/results/${batchId}`)}
                    style={{ flex: 1, justifyContent: "center" }}
                  >
                    View Full Results
                  </button>
                  <button
                    className="btn-secondary"
                    onClick={() => { setBatchId(null); setBatchData(null); }}
                  >
                    Upload Another
                  </button>
                </div>
              )}

              {!isComplete && (
                <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "16px", textAlign: "center" }}>
                  Processing... Polling every 2 seconds
                </p>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
