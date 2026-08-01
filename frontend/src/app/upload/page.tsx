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
  RefreshCw,
  Clock,
  XCircle,
} from "lucide-react";

const ALLOWED_EXTENSIONS = [".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".webm", ".opus", ".zip"];
const POLL_INTERVAL_MS = 5_000;          // 5 seconds between polls
const MAX_POLL_DURATION_MS = 5 * 60_000; // 5 minutes max polling
const MAX_CONSECUTIVE_ERRORS = 5;

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
  const [pollingTimedOut, setPollingTimedOut] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const elapsedRef = useRef<NodeJS.Timeout | null>(null);
  const pollStartRef = useRef<number>(0);
  const consecutiveErrorsRef = useRef<number>(0);

  useEffect(() => {
    const token = localStorage.getItem("autoace_token");
    if (!token) router.push("/login");
  }, []);

  // Poll for batch status
  useEffect(() => {
    if (!batchId) return;

    pollStartRef.current = Date.now();
    consecutiveErrorsRef.current = 0;
    setPollingTimedOut(false);
    setElapsedSeconds(0);

    // Elapsed timer (ticks every second)
    elapsedRef.current = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - pollStartRef.current) / 1000));
    }, 1000);

    // Status polling
    const poll = async () => {
      // Check max polling duration
      if (Date.now() - pollStartRef.current > MAX_POLL_DURATION_MS) {
        clearInterval(pollRef.current!);
        clearInterval(elapsedRef.current!);
        setPollingTimedOut(true);
        return;
      }

      try {
        const data = await getBatch(batchId);
        setBatchData(data);
        consecutiveErrorsRef.current = 0;

        if (data.status === "completed" || data.status === "failed" || data.status === "partial") {
          clearInterval(pollRef.current!);
          clearInterval(elapsedRef.current!);
        }
      } catch {
        consecutiveErrorsRef.current += 1;
        if (consecutiveErrorsRef.current >= MAX_CONSECUTIVE_ERRORS) {
          clearInterval(pollRef.current!);
          clearInterval(elapsedRef.current!);
          setPollingTimedOut(true);
        }
      }
    };

    // First poll immediately
    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      clearInterval(pollRef.current!);
      clearInterval(elapsedRef.current!);
    };
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

  function resetBatch() {
    setBatchId(null);
    setBatchData(null);
    setPollingTimedOut(false);
    setElapsedSeconds(0);
    setError("");
    setValidationWarnings([]);
    consecutiveErrorsRef.current = 0;
  }

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

  function formatElapsed(s: number): string {
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}m ${sec}s`;
  }

  const progress = batchData
    ? Math.round(((batchData.completed_files + batchData.failed_files) / Math.max(batchData.total_files, 1)) * 100)
    : 0;

  const isComplete = batchData?.status === "completed" || batchData?.status === "partial";
  const isFailed = batchData?.status === "failed";
  const isTerminal = isComplete || isFailed;
  const isProcessing = batchId && !isTerminal && !pollingTimedOut;

  // Collect failed file error messages
  const failedFiles = batchData?.results?.filter((r) => r.status === "failed") || [];

  return (
    <div className="gradient-bg" style={{ minHeight: "100vh" }}>
      <Sidebar />
      <main className="main-content">
        <div style={{ maxWidth: "760px" }}>
          {/* Header */}
          <div style={{ marginBottom: "32px" }}>
            <h1 style={{ fontSize: "26px", fontWeight: "700", letterSpacing: "-0.02em", marginBottom: "4px" }}>
              Upload File
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
          {batchId && (batchData || pollingTimedOut) && (
            <div className="glass-card animate-fade-in" style={{ padding: "28px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
                <div>
                  <h2 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "4px" }}>Batch Processing</h2>
                  <code style={{ fontSize: "12px", color: "#4338ca", background: "#e0e7ff", padding: "2px 8px", borderRadius: "6px", fontWeight: "600" }}>
                    {batchId}
                  </code>
                </div>
                {batchData && (
                  <span className={`badge ${STATUS_COLORS[batchData.status]}`}>
                    {STATUS_LABELS[batchData.status]}
                  </span>
                )}
                {pollingTimedOut && !batchData && (
                  <span className="badge bg-red-50 text-red-700 border-red-200">Timed Out</span>
                )}
              </div>

              {/* ── Polling Timeout Error ─────────────────────────────────── */}
              {pollingTimedOut && !isTerminal && (
                <div
                  style={{
                    padding: "16px",
                    background: "#fef2f2",
                    border: "1px solid #fecaca",
                    borderRadius: "12px",
                    marginBottom: "20px",
                  }}
                >
                  <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                    <Clock size={18} style={{ color: "#dc2626", flexShrink: 0, marginTop: "2px" }} />
                    <div>
                      <p style={{ fontWeight: "600", fontSize: "14px", color: "#991b1b", marginBottom: "4px" }}>
                        Processing timed out
                      </p>
                      <p style={{ fontSize: "13px", color: "#b91c1c", lineHeight: "1.5" }}>
                        The server did not respond within 5 minutes. This is likely due to the free-tier server being slow or overloaded.
                        The processing may still be running in the background — try refreshing later, or retry the upload.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Batch Failed Error Banner ─────────────────────────────── */}
              {isFailed && (
                <div
                  style={{
                    padding: "16px",
                    background: "#fef2f2",
                    border: "1px solid #fecaca",
                    borderRadius: "12px",
                    marginBottom: "20px",
                  }}
                >
                  <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                    <XCircle size={18} style={{ color: "#dc2626", flexShrink: 0, marginTop: "2px" }} />
                    <div>
                      <p style={{ fontWeight: "600", fontSize: "14px", color: "#991b1b", marginBottom: "4px" }}>
                        Processing failed
                      </p>
                      <p style={{ fontSize: "13px", color: "#b91c1c", lineHeight: "1.5" }}>
                        {batchData && batchData.failed_files > 0
                          ? `${batchData.failed_files} of ${batchData.total_files} file${batchData.total_files !== 1 ? "s" : ""} failed to process.`
                          : "All files failed to process."}
                        {" "}This may be caused by server timeouts on the free tier, unsupported audio formats, or corrupted files.
                      </p>
                    </div>
                  </div>

                  {/* Individual file errors */}
                  {failedFiles.length > 0 && (
                    <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px solid #fecaca" }}>
                      <p style={{ fontSize: "12px", fontWeight: "600", color: "#991b1b", marginBottom: "8px" }}>
                        Error details:
                      </p>
                      {failedFiles.map((f) => (
                        <div
                          key={f.filename}
                          style={{
                            display: "flex",
                            gap: "8px",
                            alignItems: "flex-start",
                            fontSize: "12px",
                            color: "#b91c1c",
                            marginBottom: "4px",
                            lineHeight: "1.4",
                          }}
                        >
                          <span style={{ fontWeight: "500", flexShrink: 0 }}>{f.filename}:</span>
                          <span>{f.error_message || "Unknown error"}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Progress bar */}
              {batchData && (
                <div style={{ marginBottom: "24px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>
                    <span>{batchData.completed_files + batchData.failed_files} / {batchData.total_files} files</span>
                    <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                      {elapsedSeconds > 0 && (
                        <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                          <Clock size={12} />
                          {formatElapsed(elapsedSeconds)}
                        </span>
                      )}
                      <span>{progress}%</span>
                    </div>
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${progress}%`,
                        background: isFailed
                          ? "linear-gradient(90deg, #ef4444, #dc2626)"
                          : undefined,
                      }}
                    />
                  </div>
                </div>
              )}

              {/* File results */}
              {batchData && batchData.results.length > 0 && (
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
                        <XCircle size={14} style={{ color: "var(--danger)", flexShrink: 0 }} />
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
                      {result.status === "failed" && result.error_message && (
                        <span
                          style={{
                            fontSize: "11px",
                            color: "#dc2626",
                            fontWeight: "500",
                            maxWidth: "200px",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                          title={result.error_message}
                        >
                          {result.error_message}
                        </span>
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

              {/* Actions — Success */}
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
                    onClick={resetBatch}
                  >
                    Upload Another
                  </button>
                </div>
              )}

              {/* Actions — Failed or Timed Out */}
              {(isFailed || pollingTimedOut) && !isComplete && (
                <div style={{ display: "flex", gap: "12px", marginTop: "24px" }}>
                  <button
                    className="btn-primary"
                    onClick={resetBatch}
                    style={{ flex: 1, justifyContent: "center", gap: "8px" }}
                  >
                    <RefreshCw size={16} />
                    Retry Upload
                  </button>
                </div>
              )}

              {/* Still processing */}
              {isProcessing && (
                <div style={{ marginTop: "16px", textAlign: "center" }}>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    Processing... Polling every 5 seconds
                  </p>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px", opacity: 0.7 }}>
                    Free-tier servers may take 1–2 minutes per file
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Loading state before first poll response */}
          {batchId && !batchData && !pollingTimedOut && (
            <div className="glass-card animate-fade-in" style={{ padding: "28px", textAlign: "center" }}>
              <div className="animate-spin" style={{ width: "24px", height: "24px", border: "3px solid var(--border)", borderTopColor: "var(--accent)", borderRadius: "50%", margin: "0 auto 16px" }} />
              <p style={{ fontSize: "14px", fontWeight: "500", color: "var(--text-primary)", marginBottom: "4px" }}>
                Processing started
              </p>
              <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Waiting for server response...
              </p>
              {elapsedSeconds > 0 && (
                <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "8px", display: "flex", alignItems: "center", justifyContent: "center", gap: "4px" }}>
                  <Clock size={12} /> {formatElapsed(elapsedSeconds)}
                </p>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
