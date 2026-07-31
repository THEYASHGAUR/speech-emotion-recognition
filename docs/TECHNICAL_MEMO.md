# Technical Memo — AutoAce AI

## Overview

AutoAce AI is an enterprise-grade audio analysis system that evaluates customer call
recordings across six dimensions using a combination of pretrained ML models and
deterministic signal processing.

---

## Approaches Evaluated

### Emotion Recognition

| Approach | Pros | Cons | Selected? |
|----------|------|------|-----------|
| wav2vec2 (HuggingFace) | SOTA accuracy, no training needed | Large model (~300MB), slow CPU | ✅ Yes |
| MFCC + SVM | Fast, interpretable | Lower accuracy, needs labeled data | ❌ No |
| GPT-4 Audio | Highest accuracy | Expensive ($0.006/min), API dependency | ❌ No |
| Whisper + text emotion | No audio model needed | Indirect, misses prosody | ❌ No |

**Selected**: `ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition`
- End-to-end audio model
- No text transcription needed
- Loaded once at startup, ~0.3s per inference on CPU

### Background Noise Detection

| Approach | Pros | Cons | Selected? |
|----------|------|------|-----------|
| Spectral feature classifier | No model, fast, interpretable | Heuristic, may misclassify | ✅ Yes |
| YAMNet audio event model | High accuracy, 521 classes | 30MB extra model, GPU preferred | Considered |
| PANNs | Research SOTA | Complex integration | ❌ No |

**Selected**: Rule-based spectral classifier using centroid, rolloff, ZCR, MFCC, rhythm detection.

### Audio Quality

All signal-processing. No ML model needed. Measures SNR, clipping, echo (autocorrelation), muffling (spectral rolloff).

### Silence Detection

librosa energy-based VAD with configurable threshold. Well-established approach for telephony.

### Speaker Overlap

Spectral flatness + harmonic energy analysis. Pyannote.audio would give higher accuracy but requires HF token and is heavyweight (~1GB).

---

## Model Selection Rationale

### wav2vec2 for Emotion
- Pre-trained on 53 languages (XLSR), fine-tuned on emotion data
- Zero training required
- Runs on CPU in ~300-800ms per audio file
- Strong baseline, particularly for English call center audio
- Label mapping is deterministic and auditable

---

## Tradeoffs

| Feature | Choice | Tradeoff |
|---------|--------|----------|
| Batch store | In-memory dict | Simple; not persistent across restarts |
| Speaker overlap | Signal processing | Lower accuracy vs. pyannote diarization |
| Deployment | uvicorn single worker | Safe for ML (GIL); scale with multiple processes |
| Authentication | JWT in env vars | Simple; no DB needed; not suitable for multi-tenant |

---

## Limitations

1. **No speaker diarization** — Overlap detection is heuristic, not diarization-based
2. **In-memory batch store** — Batches lost on restart (production: use Redis or PostgreSQL)
3. **Single-worker** — ML models not thread-safe with multi-worker uvicorn
4. **English-biased emotion model** — XLSR helps but accuracy drops on non-English audio
5. **No streaming** — Full file must upload before processing begins

---

## Future Improvements

1. Add Redis for persistent batch storage and job queuing (Celery)
2. Replace heuristic overlap with pyannote.audio diarization
3. Add Whisper transcription for text-based emotion corroboration
4. Implement model ensemble for higher accuracy
5. Add WebSocket real-time progress instead of polling
6. Add per-user quota and rate limiting
7. Support streaming audio chunks for real-time analysis
