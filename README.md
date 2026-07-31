# AutoAce AI

> Production-ready AI system for customer call recording analysis.  
> Predicts emotional tone, background noise, audio quality, speaker overlap, and silence.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- ffmpeg (installed in PATH)
- Docker & docker-compose (for containerized deployment)

### 1. Backend Setup

```bash
cd backend
cp .env.example .env        # Edit .env with your settings
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
cp .env.local.example .env.local    # Edit with your settings
npm install
npm run dev
```

### 3. Docker (All-in-one)

```bash
cp .env.example .env    # Set AUTH_PASSWORD, SECRET_KEY, NEXTAUTH_SECRET
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Default Credentials

| Field    | Value           |
|----------|-----------------|
| Username | `admin`         |
| Password | Set in `.env`   |

---

## Environment Variables

See [`backend/.env.example`](./backend/.env.example) and [`frontend/.env.local.example`](./frontend/.env.local.example) for all configuration options.

---

## Architecture

See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)

## API Documentation

See [`docs/API.md`](./docs/API.md) or visit `/docs` on a running backend.

## Deployment

See [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md)

## Technical Memo

See [`docs/TECHNICAL_MEMO.md`](./docs/TECHNICAL_MEMO.md)

---

## Project Structure

```
autoAce/
├── backend/
│   ├── app/
│   │   ├── api/routes/         # FastAPI route handlers
│   │   ├── services/           # ML service modules
│   │   │   ├── emotion/        # Speech emotion recognition
│   │   │   ├── noise/          # Background noise detection
│   │   │   ├── quality/        # Audio quality analysis
│   │   │   ├── silence/        # Long silence detection
│   │   │   ├── overlap/        # Speaker overlap detection
│   │   │   ├── confidence/     # Confidence score calculation
│   │   │   └── pipeline/       # Batch processing orchestrator
│   │   ├── schemas/            # Pydantic models
│   │   ├── utils/              # Audio, CSV, auth utilities
│   │   ├── config.py           # All configuration (env-driven)
│   │   └── main.py             # FastAPI app factory
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js App Router pages
│   │   ├── components/         # Reusable UI components
│   │   └── lib/                # API client, hooks, utils
│   └── Dockerfile
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DEPLOYMENT.md
│   ├── TECHNICAL_MEMO.md
│   ├── COST_ANALYSIS.md
│   └── LATENCY_ANALYSIS.md
└── docker-compose.yml
```
