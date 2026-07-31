# Cost Analysis — AutoAce AI

## Target: < $0.003 per audio minute

---

## CPU-Only Deployment (Default)

| Component | Time per min audio | Cost Basis |
|-----------|-------------------|------------|
| Emotion (wav2vec2 CPU) | ~15–30s | Compute cost |
| Noise (librosa) | ~0.3s | Negligible |
| Quality (librosa) | ~0.1s | Negligible |
| Silence (librosa) | ~0.1s | Negligible |
| Overlap (librosa) | ~0.2s | Negligible |
| Total per 1-min file | ~16–31s | |

### Cloud: Railway / Render (Hobby/Starter tier)
- 1 vCPU, 512MB RAM: ~$7/month
- Processes ~120–230 audio minutes/hour
- **Cost per audio minute: $7 / (720 hours × 170 avg) ≈ $0.000057/min**

### Cloud: 1× AWS t3.medium (2 vCPU, 4GB RAM)
- $0.0416/hour on-demand
- Processes ~300 audio minutes/hour
- **Cost per audio minute: $0.0416 / 300 ≈ $0.000139/min**

---

## GPU Deployment (Optional)

| Component | Time per min audio |
|-----------|-------------------|
| Emotion (wav2vec2 T4 GPU) | ~1–3s |
| Others (CPU) | ~0.7s |
| Total per 1-min file | ~1.7–3.7s |

### Cloud: 1× AWS g4dn.xlarge (T4 GPU)
- $0.526/hour
- Processes ~1,600 audio minutes/hour
- **Cost per audio minute: $0.526 / 1600 ≈ $0.000329/min**

---

## Summary

| Deployment | Cost per Audio Minute | vs. $0.003 Target |
|------------|----------------------|-------------------|
| CPU (t3.medium) | $0.000139 | **21× below target** |
| GPU (T4) | $0.000329 | **9× below target** |
| CPU (Railway Hobby) | $0.000057 | **52× below target** |

**All deployment options comfortably meet the $0.003/minute target.**

---

## Memory Requirements

| Component | Memory |
|-----------|--------|
| wav2vec2 model | ~350MB |
| OS + Python runtime | ~200MB |
| Audio buffers (batch=4) | ~50MB |
| **Total minimum** | **~600MB RAM** |

Recommended: 1GB+ RAM for stable operation.

---

## Storage

| Data | Size estimate |
|------|--------------|
| Per audio minute | ~1MB (WAV) |
| Model cache | ~350MB (one-time download) |
| Results (JSON/CSV) | ~1KB per file |
