/* eslint-disable react-hooks/static-components */
"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import {
  getBatch,
  BatchResponse,
  FileResult,
  AudioAnalysis,
  EmotionalTone,
  AudioQuality,
  BatchStatus,
  exportBatchCsv,
} from "@/lib/api";
import {
  EMOTION_LABELS,
  EMOTION_COLORS,
  EMOTION_EMOJI,
  QUALITY_LABELS,
  QUALITY_COLORS,
  STATUS_LABELS,
  STATUS_COLORS,
  INTENSITY_LABELS,
  INTENSITY_COLORS,
  confidenceColor,
  formatDuration,
  formatDate,
} from "@/lib/utils";
import {
  Download,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  Filter,
  FileAudio,
} from "lucide-react";

type SortField = "filename" | "emotional_tone" | "audio_quality" | "confidence" | "audio_duration_seconds";
type SortDir = "asc" | "desc";

export default function ResultsPage() {
  const router = useRouter();
  const params = useParams();
  const batchId = params.batchId as string;

  const [batch, setBatch] = useState<BatchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  // Filters
  const [filterEmotion, setFilterEmotion] = useState<EmotionalTone | "">("");
  const [filterQuality, setFilterQuality] = useState<AudioQuality | "">("");
  const [filterStatus, setFilterStatus] = useState<"completed" | "failed" | "">("");
  const [filterNoise, setFilterNoise] = useState<"" | "true" | "false">("");
  const [filterOverlap, setFilterOverlap] = useState<"" | "true" | "false">("");
  const [filterSilence, setFilterSilence] = useState<"" | "true" | "false">("");
  const [searchQuery, setSearchQuery] = useState("");

  // Sorting
  const [sortField, setSortField] = useState<SortField>("filename");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  useEffect(() => {
    const token = localStorage.getItem("autoace_token");
    if (!token) { router.push("/login"); return; }
    fetchBatch();
  }, [batchId]);

  // Poll while processing
  useEffect(() => {
    if (!batch || batch.status === "completed" || batch.status === "failed" || batch.status === "partial") return;
    const t = setInterval(fetchBatch, 3000);
    return () => clearInterval(t);
  }, [batch?.status]);

  async function fetchBatch() {
    try {
      const data = await getBatch(batchId);
      setBatch(data);
    } catch {
      setError("Batch not found or failed to load.");
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      await exportBatchCsv(batchId);
    } catch {
      setError("Export failed.");
    } finally {
      setExporting(false);
    }
  }

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  }

  const filteredResults = useMemo(() => {
    if (!batch) return [];
    let results = batch.results.filter((r) => r.status === "completed" || r.status === "failed");

    if (filterStatus) results = results.filter((r) => r.status === filterStatus);
    if (filterEmotion) results = results.filter((r) => r.analysis?.emotional_tone === filterEmotion);
    if (filterQuality) results = results.filter((r) => r.analysis?.audio_quality === filterQuality);
    if (filterNoise !== "") results = results.filter((r) => r.analysis?.background_noise_present === (filterNoise === "true"));
    if (filterOverlap !== "") results = results.filter((r) => r.analysis?.speaker_overlap_present === (filterOverlap === "true"));
    if (filterSilence !== "") results = results.filter((r) => r.analysis?.long_silence_present === (filterSilence === "true"));
    if (searchQuery) results = results.filter((r) => r.filename.toLowerCase().includes(searchQuery.toLowerCase()));

    return results.sort((a, b) => {
      let aVal: string | number = "";
      let bVal: string | number = "";

      if (sortField === "filename") { aVal = a.filename; bVal = b.filename; }
      else if (sortField === "emotional_tone") { aVal = a.analysis?.emotional_tone ?? ""; bVal = b.analysis?.emotional_tone ?? ""; }
      else if (sortField === "audio_quality") { aVal = a.analysis?.audio_quality ?? ""; bVal = b.analysis?.audio_quality ?? ""; }
      else if (sortField === "confidence") { aVal = a.analysis?.confidence ?? -1; bVal = b.analysis?.confidence ?? -1; }
      else if (sortField === "audio_duration_seconds") { aVal = a.audio_duration_seconds ?? 0; bVal = b.audio_duration_seconds ?? 0; }

      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDir === "asc" ? aVal - bVal : bVal - aVal;
      }
      return 0;
    });
  }, [batch, filterEmotion, filterQuality, filterStatus, filterNoise, filterOverlap, filterSilence, searchQuery, sortField, sortDir]);

  function SortIcon({ field }: { field: SortField }) {
    if (sortField !== field) return <ArrowUpDown size={12} style={{ opacity: 0.4 }} />;
    return sortDir === "asc" ? <ArrowUp size={12} /> : <ArrowDown size={12} />;
  }

  const isProcessing = batch?.status === "processing" || batch?.status === "uploading" || batch?.status === "validating";
  const progress = batch ? Math.round(((batch.completed_files + batch.failed_files) / Math.max(batch.total_files, 1)) * 100) : 0;

  if (loading) {
    return (
      <div className="gradient-bg" style={{ minHeight: "100vh" }}>
        <Sidebar />
        <main className="main-content" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ textAlign: "center", color: "var(--text-muted)" }}>
            <div className="animate-spin" style={{ width: "32px", height: "32px", border: "3px solid var(--border)", borderTopColor: "var(--accent)", borderRadius: "50%", margin: "0 auto 16px" }} />
            Loading results...
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="gradient-bg" style={{ minHeight: "100vh" }}>
      <Sidebar />
      <main className="main-content">
        {/* Header */}
        <div style={{ marginBottom: "28px" }}>
          <button
            onClick={() => router.push("/history")}
            className="btn-secondary"
            style={{ padding: "6px 12px", fontSize: "12px", marginBottom: "16px" }}
          >
            <ChevronLeft size={14} /> Back to History
          </button>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <h1 style={{ fontSize: "24px", fontWeight: "700", letterSpacing: "-0.02em", marginBottom: "4px" }}>
                Results
              </h1>
              <code style={{ fontSize: "12px", color: "#4338ca", background: "#e0e7ff", padding: "2px 10px", borderRadius: "6px", fontWeight: "600" }}>
                {batchId}
              </code>
            </div>
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              {batch && (
                <span className={`badge ${STATUS_COLORS[batch.status]}`}>
                  {STATUS_LABELS[batch.status]}
                </span>
              )}
              <button onClick={fetchBatch} className="btn-secondary" style={{ padding: "8px 12px" }}>
                <RefreshCw size={14} />
              </button>
              {batch?.status !== "processing" && (
                <button
                  id="export-csv-btn"
                  className="btn-primary"
                  onClick={handleExport}
                  disabled={exporting}
                >
                  {exporting ? (
                    <div className="animate-spin" style={{ width: "14px", height: "14px", border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "white", borderRadius: "50%" }} />
                  ) : (
                    <Download size={14} />
                  )}
                  Export CSV
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Processing progress */}
        {isProcessing && batch && (
          <div className="glass-card" style={{ padding: "20px 24px", marginBottom: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px", fontSize: "13px", color: "var(--text-secondary)" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div className="animate-spin" style={{ width: "14px", height: "14px", border: "2px solid var(--border)", borderTopColor: "var(--accent)", borderRadius: "50%" }} />
                Processing...
              </span>
              <span>{batch.completed_files + batch.failed_files} / {batch.total_files} files ({progress}%)</span>
            </div>
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
            </div>
          </div>
        )}

        {/* Summary stats */}
        {batch?.summary && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "24px" }}>
            {[
              { label: "Completed", value: batch.summary.completed_files, color: "var(--success)" },
              { label: "Failed", value: batch.summary.failed_files, color: "var(--danger)" },
              { label: "Avg Confidence", value: batch.summary.avg_confidence ? `${(batch.summary.avg_confidence * 100).toFixed(1)}%` : "—", color: "var(--accent)" },
              { label: "Processing Time", value: batch.summary.processing_time_seconds ? formatDuration(batch.summary.processing_time_seconds) : "—", color: "var(--text-secondary)" },
            ].map(({ label, value, color }) => (
              <div key={label} className="stat-card" style={{ padding: "14px 18px" }}>
                <p style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "4px" }}>{label}</p>
                <p style={{ fontSize: "22px", fontWeight: "700", color }}>{value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Filters */}
        <div className="glass-card" style={{ padding: "14px 18px", marginBottom: "16px", display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "center" }}>
          <Filter size={14} style={{ color: "var(--text-muted)" }} />
          <input
            className="input"
            placeholder="Search filename..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: "180px", padding: "6px 10px", fontSize: "12px" }}
          />
          <select className="select" value={filterEmotion} onChange={(e) => setFilterEmotion(e.target.value as EmotionalTone | "")}>
            <option value="">All Emotions</option>
            {(["neutral", "satisfied", "frustrated", "upset", "distressed"] as EmotionalTone[]).map((e) => (
              <option key={e} value={e}>{EMOTION_LABELS[e]}</option>
            ))}
          </select>
          <select className="select" value={filterQuality} onChange={(e) => setFilterQuality(e.target.value as AudioQuality | "")}>
            <option value="">All Quality</option>
            {(["clear", "slightly_impaired", "severely_impaired"] as AudioQuality[]).map((q) => (
              <option key={q} value={q}>{QUALITY_LABELS[q]}</option>
            ))}
          </select>
          <select className="select" value={filterNoise} onChange={(e) => setFilterNoise(e.target.value as "" | "true" | "false")}>
            <option value="">Noise: All</option>
            <option value="true">Noise Present</option>
            <option value="false">No Noise</option>
          </select>
          <select className="select" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value as "completed" | "failed" | "")}>
            <option value="">All Status</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
          {(filterEmotion || filterQuality || filterNoise || filterStatus || filterOverlap || filterSilence || searchQuery) && (
            <button
              onClick={() => { setFilterEmotion(""); setFilterQuality(""); setFilterNoise(""); setFilterStatus(""); setFilterOverlap(""); setFilterSilence(""); setSearchQuery(""); }}
              style={{ background: "none", border: "none", color: "var(--accent)", cursor: "pointer", fontSize: "12px", fontWeight: "500" }}
            >
              Clear filters
            </button>
          )}
          <span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--text-muted)" }}>
            {filteredResults.length} results
          </span>
        </div>

        {/* Error */}
        {error && (
          <div style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "10px", color: "#dc2626", fontSize: "13px", marginBottom: "16px" }}>
            {error}
          </div>
        )}

        {/* Results table */}
        <div className="glass-card" style={{ overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ cursor: "pointer" }} onClick={() => toggleSort("filename")}>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>Filename <SortIcon field="filename" /></span>
                  </th>
                  <th style={{ cursor: "pointer" }} onClick={() => toggleSort("emotional_tone")}>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>Emotion <SortIcon field="emotional_tone" /></span>
                  </th>
                  <th>Intensity</th>
                  <th>Noise</th>
                  <th>Noise Type</th>
                  <th style={{ cursor: "pointer" }} onClick={() => toggleSort("audio_quality")}>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>Quality <SortIcon field="audio_quality" /></span>
                  </th>
                  <th>Overlap</th>
                  <th>Silence</th>
                  <th style={{ cursor: "pointer" }} onClick={() => toggleSort("confidence")}>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>Confidence <SortIcon field="confidence" /></span>
                  </th>
                  <th style={{ cursor: "pointer" }} onClick={() => toggleSort("audio_duration_seconds")}>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>Duration <SortIcon field="audio_duration_seconds" /></span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.length === 0 ? (
                  <tr>
                    <td colSpan={10}>
                      <div className="empty-state">
                        <FileAudio size={32} />
                        <p>No results match your filters</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredResults.map((result) => (
                    <tr key={result.filename}>
                      <td style={{ maxWidth: "200px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          {result.status === "completed" ? (
                            <CheckCircle2 size={14} style={{ color: "var(--success)", flexShrink: 0 }} />
                          ) : (
                            <AlertCircle size={14} style={{ color: "var(--danger)", flexShrink: 0 }} />
                          )}
                          <span style={{ fontSize: "12px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--text-primary)", fontWeight: "500" }} title={result.filename}>
                            {result.filename}
                          </span>
                        </div>
                        {result.error_message && (
                          <div style={{ fontSize: "10px", color: "#dc2626", marginTop: "2px" }}>{result.error_message}</div>
                        )}
                      </td>
                      {result.analysis ? (
                        <>
                          <td>
                            <span className={`badge ${EMOTION_COLORS[result.analysis.emotional_tone]}`}>
                              {EMOTION_EMOJI[result.analysis.emotional_tone]} {EMOTION_LABELS[result.analysis.emotional_tone]}
                            </span>
                          </td>
                          <td>
                            <span className={`badge ${INTENSITY_COLORS[result.analysis.emotional_intensity]}`}>
                              {INTENSITY_LABELS[result.analysis.emotional_intensity]}
                            </span>
                          </td>
                          <td>
                            <span style={{ color: result.analysis.background_noise_present ? "#b45309" : "var(--text-muted)", fontSize: "12px", fontWeight: "600" }}>
                              {result.analysis.background_noise_present ? "Yes" : "No"}
                            </span>
                          </td>
                          <td style={{ fontSize: "12px", color: "var(--text-secondary)", textTransform: "capitalize" }}>
                            {result.analysis.background_noise_type.replace("_", " ")}
                          </td>
                          <td>
                            <span className={`badge ${QUALITY_COLORS[result.analysis.audio_quality]}`}>
                              {QUALITY_LABELS[result.analysis.audio_quality]}
                            </span>
                          </td>
                          <td style={{ fontSize: "12px", color: result.analysis.speaker_overlap_present ? "#b45309" : "var(--text-muted)", fontWeight: "600" }}>
                            {result.analysis.speaker_overlap_present ? "Yes" : "No"}
                          </td>
                          <td style={{ fontSize: "12px", color: result.analysis.long_silence_present ? "#b45309" : "var(--text-muted)", fontWeight: "600" }}>
                            {result.analysis.long_silence_present ? "Yes" : "No"}
                          </td>
                          <td>
                            <span className={`confidence-ring ${confidenceColor(result.analysis.confidence)}`}>
                              <svg width="28" height="28" viewBox="0 0 28 28">
                                <circle cx="14" cy="14" r="11" fill="none" stroke="#e2e8f0" strokeWidth="2.5" />
                                <circle cx="14" cy="14" r="11" fill="none" stroke="currentColor" strokeWidth="2.5"
                                  strokeDasharray={`${2 * Math.PI * 11 * result.analysis.confidence} ${2 * Math.PI * 11}`}
                                  strokeLinecap="round"
                                  transform="rotate(-90 14 14)"
                                />
                              </svg>
                              {(result.analysis.confidence * 100).toFixed(0)}%
                            </span>
                          </td>
                          <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                            {formatDuration(result.audio_duration_seconds)}
                          </td>
                        </>
                      ) : (
                        <td colSpan={9} style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                          —
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
