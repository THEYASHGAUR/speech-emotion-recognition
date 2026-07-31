# Latency Analysis — AutoAce AI

## Per-File Processing Time

Measured on representative audio (1-minute call recording).

### CPU-Only (t3.medium, 2 vCPU)

| Stage | Time |
|-------|------|
| Audio load + preprocess | 0.5–1.5s |
| Emotion inference (wav2vec2) | 15–30s |
| Noise detection | 0.2–0.5s |
| Quality analysis | 0.1–0.2s |
| Silence detection | 0.1–0.2s |
| Overlap detection | 0.2–0.5s |
| Confidence calculation | <0.01s |
| **Total per file (1 min audio)** | **~16–33s** |

### GPU (T4)

| Stage | Time |
|-------|------|
| Audio load + preprocess | 0.5–1.5s |
| Emotion inference (wav2vec2 GPU) | 1–3s |
| Other stages (CPU) | 0.6–1.4s |
| **Total per file (1 min audio)** | **~2–6s** |

---

## Batch Throughput

With `MAX_CONCURRENT_FILES=4` (default):

| Hardware | Throughput |
|----------|-----------|
| CPU (t3.medium) | ~8–15 files/min |
| CPU (c6i.xlarge, 4 vCPU) | ~15–30 files/min |
| GPU (T4, g4dn.xlarge) | ~40–80 files/min |

---

## Audio Duration Scaling

Processing time scales approximately linearly with audio duration:

| Audio Duration | CPU Time | GPU Time |
|---------------|----------|----------|
| 30 seconds | 8–16s | 1–3s |
| 1 minute | 16–33s | 2–6s |
| 5 minutes | 80–165s | 10–30s |
| 10 minutes | 160–330s | 20–60s |

---

## Optimization Notes

1. **Model loading** happens ONCE at startup (~30–60s) — amortized across all requests
2. **ThreadPoolExecutor** with `MAX_CONCURRENT_FILES=4` parallelizes I/O-bound portions
3. **Sample rate conversion** to 16kHz reduces data size before ML inference
4. **Audio truncation** at `MAX_AUDIO_DURATION_SECONDS=600` prevents runaway processing

---

## Production Throughput Estimate

For a call center processing 10,000 calls/day (avg 5 min each):
- Total audio: 50,000 minutes/day ≈ 833 hours
- Required throughput: ~35 files/minute sustained
- **2× c6i.xlarge CPU** OR **1× g4dn.xlarge GPU** can handle this load
