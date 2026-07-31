# Deployment Guide — AutoAce AI

## Option 1: Docker Compose (Recommended)

### Prerequisites
- Docker Engine 24+
- docker-compose v2+

### Steps

```bash
# 1. Clone the repository
git clone <your-repo-url> && cd autoAce

# 2. Configure environment
cp .env.example .env
# Edit .env:
#   AUTH_PASSWORD=your-strong-password
#   SECRET_KEY=$(openssl rand -hex 32)
#   NEXTAUTH_SECRET=$(openssl rand -hex 32)

# 3. Build and start
docker-compose up --build -d

# 4. Verify
curl http://localhost:8000/health
```

**Frontend**: http://localhost:3000  
**API Docs**: http://localhost:8000/docs

---

## Option 2: Railway

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login

# Deploy backend
cd backend
railway init
railway up

# Set env vars in Railway dashboard:
# AUTH_PASSWORD, SECRET_KEY, HUGGINGFACE_TOKEN (optional)

# Deploy frontend
cd ../frontend
railway init
railway up

# Set env vars:
# NEXT_PUBLIC_API_URL=https://your-backend.railway.app
# NEXTAUTH_SECRET, NEXTAUTH_URL
```

---

## Option 3: Render

1. Connect GitHub repo to Render
2. Create **Web Service** for backend:
   - Root: `backend/`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Create **Web Service** for frontend:
   - Root: `frontend/`
   - Build: `npm ci && npm run build`
   - Start: `npm start`

---

## Option 4: Google Cloud Run

```bash
# Backend
gcloud run deploy autoace-backend \
  --source ./backend \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300s \
  --set-env-vars AUTH_PASSWORD=... \
  --allow-unauthenticated

# Frontend
gcloud run deploy autoace-frontend \
  --source ./frontend \
  --region us-central1 \
  --set-env-vars NEXT_PUBLIC_API_URL=https://autoace-backend-xxx.run.app
```

---

## Environment Variables Reference

### Backend
| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH_PASSWORD` | ✅ | Login password |
| `SECRET_KEY` | ✅ | JWT signing key (32+ chars) |
| `HUGGINGFACE_TOKEN` | ❌ | For gated HF models |
| `MAX_CONCURRENT_FILES` | ❌ | Default: 4 |

### Frontend
| Variable | Required | Description |
|----------|----------|-------------|
| `NEXTAUTH_SECRET` | ✅ | NextAuth signing key |
| `NEXTAUTH_URL` | ✅ | Full frontend URL |
| `NEXT_PUBLIC_API_URL` | ✅ | Backend API URL |

---

## First-Run Notes

- The emotion model (~350MB) downloads on first startup from HuggingFace Hub
- Subsequent starts use the cached model
- Set `EMOTION_MODEL_CACHE_DIR` to a persistent volume for Docker deployments
