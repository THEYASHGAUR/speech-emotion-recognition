# Architecture — AutoAce AI

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      AutoAce AI System                       │
├──────────────────────┬──────────────────────────────────────┤
│     Frontend          │           Backend                    │
│   (Next.js 14)        │         (FastAPI)                    │
│                       │                                      │
│  ┌──────────────┐     │  ┌─────────────────────────────┐    │
│  │  Login Page  │─────┼─▶│  POST /api/v1/auth/login    │    │
│  └──────────────┘     │  └─────────────────────────────┘    │
│  ┌──────────────┐     │  ┌─────────────────────────────┐    │
│  │  Dashboard   │─────┼─▶│  GET  /api/v1/batches       │    │
│  └──────────────┘     │  └─────────────────────────────┘    │
│  ┌──────────────┐     │  ┌─────────────────────────────┐    │
│  │  Upload Page │─────┼─▶│  POST /api/v1/upload        │    │
│  └──────────────┘     │  └──────────┬──────────────────┘    │
│  ┌──────────────┐     │             │                        │
│  │ Results Page │─────┼─▶ GET batch │ Background Processing  │
│  └──────────────┘     │             ▼                        │
│  ┌──────────────┐     │  ┌─────────────────────────────┐    │
│  │ History Page │     │  │    Pipeline Processor        │    │
│  └──────────────┘     │  │                             │    │
└──────────────────────-┘  │  ┌───────────────────────┐  │    │
                            │  │ Emotion Recognizer    │  │    │
                            │  │ (wav2vec2 HuggingFace)│  │    │
                            │  ├───────────────────────┤  │    │
                            │  │ Noise Detector        │  │    │
                            │  │ (spectral analysis)   │  │    │
                            │  ├───────────────────────┤  │    │
                            │  │ Quality Analyzer      │  │    │
                            │  │ (SNR, echo, clipping) │  │    │
                            │  ├───────────────────────┤  │    │
                            │  │ Silence Detector      │  │    │
                            │  │ (VAD + librosa)       │  │    │
                            │  ├───────────────────────┤  │    │
                            │  │ Overlap Detector      │  │    │
                            │  │ (energy + spectral)   │  │    │
                            │  ├───────────────────────┤  │    │
                            │  │ Confidence Calculator │  │    │
                            │  │ (weighted ensemble)   │  │    │
                            │  └───────────────────────┘  │    │
                            └─────────────────────────────┘    │
```

## Component Descriptions

### Frontend (Next.js 14 App Router)
- **Login** — NextAuth credentials authentication
- **Dashboard** — Batch statistics overview
- **Upload** — Drag-and-drop ZIP/folder upload with progress tracking
- **Results** — Filterable, sortable results table with CSV export
- **History** — Past batch listing

### Backend (FastAPI)
- **API Routes** — Authenticated REST endpoints
- **Pipeline Processor** — ThreadPoolExecutor-based parallel processing
- **ML Services** — Six independent analysis services, all loaded at startup

### ML Services

| Service | Approach | Library |
|---------|----------|---------|
| Emotion | HuggingFace wav2vec2 | transformers |
| Noise | Spectral + acoustic features | librosa |
| Quality | SNR + echo + clipping + muffling | librosa + numpy |
| Silence | Energy-based VAD | librosa |
| Overlap | Spectral flatness + harmonic analysis | librosa |
| Confidence | Weighted multi-signal ensemble | numpy |

## Data Flow

1. User uploads ZIP (audio files + labels.csv)
2. Backend extracts, validates, assigns `batch_id`
3. Background task processes each file through the 6-stage pipeline
4. Results stored in memory (batch_store)
5. Frontend polls `GET /api/v1/batch/{id}` until complete
6. User downloads CSV export
