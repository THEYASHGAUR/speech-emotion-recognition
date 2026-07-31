# AutoAce AI Technical Trial - Complete Project Specification

Build a production-ready, full-stack AI application that analyzes uploaded customer call recordings and predicts emotional tone, emotional intensity, background noise, audio quality, speaker overlap, and long silence.

The application must be designed as if it will be deployed inside a real production environment.

---

# Tech Stack

Frontend
- Next.js (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Query
- Axios

Backend
- FastAPI
- Python 3.11+
- PyTorch
- HuggingFace Transformers
- librosa
- torchaudio
- ffmpeg
- pandas
- numpy
- scikit-learn

Deployment
- Docker
- docker-compose
- Railway / Render / Cloud Run compatible

---

# High Level Architecture

Frontend

↓

Authentication

↓

Dashboard

↓

Batch Upload

↓

FastAPI

↓

Audio Processing Pipeline

↓

Emotion Recognition

↓

Background Noise Detection

↓

Audio Quality Analysis

↓

Speaker Overlap Detection

↓

Long Silence Detection

↓

Confidence Calculation

↓

JSON Response

↓

CSV Export

---

# Folder Structure

frontend/

backend/

docs/

docker/

README.md

docker-compose.yml

---

# Backend Structure

backend/

app/

api/

services/

emotion/

noise/

quality/

overlap/

silence/

schemas/

utils/

models/

main.py

requirements.txt

---

# Step 1

Create a FastAPI backend.

Requirements

- production folder structure
- environment variables
- logging
- exception handling
- CORS
- API documentation
- request validation
- response validation

---

# Step 2

Create a Next.js frontend.

Pages

- Login
- Dashboard
- Upload File
- Results
- History (optional)

Use shadcn/ui.

---

# Step 3

Authentication

Implement simple username/password authentication.

Store credentials securely.

Session based login is sufficient.

---

# Step 4

Batch Upload

Allow user to upload

- ZIP folder

or

- Folder

The uploaded batch contains

audio files

+

labels.csv

Validate

- missing files
- unsupported files
- duplicate names
- invalid csv

Display clear validation errors.

---

# Step 5

Batch Processor

For every uploaded audio

Create processing pipeline.

Pipeline

Load audio

↓

Normalize

↓

Convert sample rate if needed

↓

Feature Extraction

↓

Emotion Model

↓

Noise Analysis

↓

Quality Analysis

↓

Silence Detection

↓

Overlap Detection

↓

Confidence

↓

Prediction JSON

Run files independently.

One failed file must not stop entire batch.

---

# Step 6

Emotion Recognition

Use a pretrained HuggingFace Speech Emotion Recognition model.

Do NOT train a model from scratch.

Load model once during FastAPI startup.

Perform inference locally using PyTorch.

Map model outputs into

neutral

satisfied

frustrated

upset

distressed

If model labels differ, implement deterministic mapping.

---

# Step 7

Background Noise Detection

Determine

background_noise_present

background_noise_type

background_noise_severity

Use hybrid approach.

Combine

signal processing

+

acoustic analysis

+

optional pretrained audio event model

Noise examples

office chatter

road noise

music

wind

keyboard

television

mechanical

none

---

# Step 8

Audio Quality Analysis

Predict

audio_quality

Possible values

clear

slightly_impaired

severely_impaired

Consider

volume

SNR

distortion

echo

clipping

packet loss indicators

static

muffling

---

# Step 9

Speaker Overlap Detection

Detect

speaker_overlap_present

Use

pyannote

or

voice activity analysis

Return boolean.

---

# Step 10

Long Silence Detection

Detect

long_silence_present

Use VAD

or librosa.

Threshold should be configurable.

---

# Step 11

Confidence Score

Return confidence

0.0

↓

1.0

Combine

model confidence

+

feature confidence

+

heuristics

Never hardcode.

---

# Step 12

Output JSON

Exactly match

{
    "emotional_tone": "...",
    "emotional_intensity": "...",
    "background_noise_present": true,
    "background_noise_type": "...",
    "background_noise_severity": "...",
    "audio_quality": "...",
    "speaker_overlap_present": false,
    "long_silence_present": false,
    "confidence": 0.91
}

Schema must exactly follow assignment.

---

# Step 13

Results Page

Display

Filename

Emotion

Intensity

Noise

Noise Severity

Quality

Overlap

Silence

Confidence

Allow filtering.

Allow sorting.

---

# Step 14

CSV Export

Export

filename

+

prediction json

Maintain original filenames.

---

# Step 15

Progress Tracking

Display

Uploading

Processing

Completed

Failed

Use polling or websocket.

---

# Step 16

Error Handling

Handle

unsupported format

corrupted file

missing audio

missing csv

invalid json

processing timeout

Display user-friendly errors.

---

# Step 17

Performance

Process multiple files sequentially or concurrently.

Avoid loading ML models for every request.

Load models only once during application startup.

---

# Step 18

Configuration

Store

model names

thresholds

upload limits

confidence thresholds

allowed formats

inside configuration files.

No hardcoded constants.

---

# Step 19

Documentation

Generate

README

Architecture Diagram

API Documentation

Deployment Guide

Setup Guide

Environment Variables

---

# Step 20

Docker

Provide

Dockerfile

docker-compose.yml

Production ready.

---

# Step 21

Deployment

Deploy frontend and backend.

Provide

URL

login credentials

Deployment should be publicly accessible.

---

# Step 22

Technical Memo

Create documentation describing

- approaches evaluated
- architecture
- model selection
- why selected
- tradeoffs
- limitations
- future improvements

---

# Step 23

Validation

Run predictions on provided labeled calls.

Compare predictions with labels.

Generate

confusion matrix

classification report

per-class metrics

overall accuracy

macro F1

---

# Step 24

Cost Analysis

Estimate

cost per audio minute

GPU assumptions

CPU assumptions

memory

storage

Show that total inference cost remains below

$0.003 per minute.

---

# Step 25

Latency Analysis

Measure

processing time

per audio

per minute

Estimate production throughput.

---

# Step 26

Coding Standards

Use

clean architecture

dependency injection where appropriate

modular services

type hints

Pydantic models

async FastAPI

structured logging

proper comments

production-quality code

No placeholder implementations.

No TODOs.

No mock predictions.

All prediction logic should be functional.

---

# Goal

The final submission should resemble an internal enterprise AI tool rather than a demo project.

Prioritize

1. Accuracy
2. Production readiness
3. Cost efficiency
4. Scalability
5. Maintainability
6. Clean architecture
7. Excellent UI/UX