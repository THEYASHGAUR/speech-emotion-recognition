# API Documentation — AutoAce AI

Base URL: `http://localhost:8000/api/v1`  
Full interactive docs: `http://localhost:8000/docs`

---

## Authentication

All endpoints except `/auth/login` require a Bearer token.

```
Authorization: Bearer <your-jwt-token>
```

---

## Endpoints

### POST /auth/login

Authenticate and receive a JWT token.

**Request:**
```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

---

### POST /upload

Upload a batch of audio files for analysis.

**Content-Type:** `multipart/form-data`

**Body:**
- `files` — One ZIP file, OR multiple audio files (+ optional `labels.csv`)

**Response (202 Accepted):**
```json
{
  "batch_id": "uuid-here",
  "message": "Batch accepted. Processing 5 files.",
  "total_files": 5,
  "validation_errors": []
}
```

---

### GET /batch/{batch_id}

Get batch status and results.

**Response:**
```json
{
  "batch_id": "uuid",
  "status": "completed",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:32:15Z",
  "total_files": 5,
  "completed_files": 5,
  "failed_files": 0,
  "results": [
    {
      "filename": "call_001.wav",
      "status": "completed",
      "analysis": {
        "emotional_tone": "frustrated",
        "emotional_intensity": "high",
        "background_noise_present": true,
        "background_noise_type": "office_chatter",
        "background_noise_severity": "medium",
        "audio_quality": "clear",
        "speaker_overlap_present": false,
        "long_silence_present": false,
        "confidence": 0.87
      },
      "processing_time_seconds": 18.4,
      "audio_duration_seconds": 62.3
    }
  ],
  "summary": {
    "total_files": 5,
    "completed_files": 5,
    "failed_files": 0,
    "avg_confidence": 0.82,
    "emotion_distribution": {"frustrated": 2, "neutral": 2, "satisfied": 1},
    "quality_distribution": {"clear": 4, "slightly_impaired": 1}
  }
}
```

**Batch Status Values:** `uploading` | `validating` | `processing` | `completed` | `partial` | `failed`

---

### GET /batch/{batch_id}/export

Download results as CSV. Available only after batch completes.

**Response:** `text/csv` file download

---

### GET /batches

List all batch jobs (newest first).

**Response:**
```json
[
  {
    "batch_id": "uuid",
    "status": "completed",
    "created_at": "...",
    "updated_at": "...",
    "total_files": 5,
    "completed_files": 5,
    "failed_files": 0
  }
]
```

---

## Output Schema

Every completed file returns this exact schema:

| Field | Type | Values |
|-------|------|--------|
| `emotional_tone` | string | `neutral`, `satisfied`, `frustrated`, `upset`, `distressed` |
| `emotional_intensity` | string | `low`, `medium`, `high` |
| `background_noise_present` | boolean | |
| `background_noise_type` | string | `office_chatter`, `road_noise`, `music`, `wind`, `keyboard`, `television`, `mechanical`, `none` |
| `background_noise_severity` | string | `low`, `medium`, `high`, `none` |
| `audio_quality` | string | `clear`, `slightly_impaired`, `severely_impaired` |
| `speaker_overlap_present` | boolean | |
| `long_silence_present` | boolean | |
| `confidence` | float | 0.0 – 1.0 |

---

## Error Responses

All errors follow this schema:

```json
{
  "detail": "Human-readable error message",
  "code": "optional_error_code",
  "path": "/api/v1/..."
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request / validation error |
| 401 | Unauthorized |
| 404 | Batch not found |
| 409 | Conflict (e.g., export before complete) |
| 413 | Upload too large |
| 500 | Internal server error |
