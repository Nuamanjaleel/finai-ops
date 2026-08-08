# FinAI Ops

> Enterprise-grade AI risk & compliance intelligence system with production-hardened FastAPI backend and high-speed LLM inference.

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://finai-ops-production.up.railway.app/docs)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED)](https://www.docker.com)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

---

## 🚀 Live Demo

**API:** https://finai-ops-production.up.railway.app  
**Interactive Docs:** https://finai-ops-production.up.railway.app/docs

---

## 📖 Overview

FinAI Ops is a production-grade GenAI backend built to demonstrate real-world enterprise AI infrastructure patterns. It accepts natural language questions about financial risk and compliance, and returns structured AI-generated answers using low-latency LLM inference.

Unlike typical tutorial projects, FinAI Ops includes the hard parts of production systems: authentication, rate limiting, caching, retry logic, structured logging, and graceful error handling.

---

## ✨ Key Features

### 🔐 Security
- API Key Authentication via X-API-Key header on protected endpoints
- Global Exception Handler with no stack trace leaks to clients

### ⚡ Performance
- TTL LRU Cache with 100-entry response cache and 1-hour TTL, reduces upstream API calls
- Groq LPU Inference — ~10x faster than GPU-based providers (avg response: 400-600ms)
- Cache hit/miss telemetry via /cache/stats endpoint

### 🛡️ Reliability
- Retry Logic with exponential backoff on transient upstream failures (Tenacity)
- Rate Limiting per-IP sliding window (10 req/min for /query)
- Graceful degradation with clean error responses on upstream unavailability

### 👁️ Observability
- Structured JSON Logging, machine-parseable, ready for Datadog/Splunk/CloudWatch
- Request ID Correlation — every request tagged with UUID, returned in X-Request-ID header
- Latency Tracking per-request in milliseconds

### 🏗️ Deployment
- Dockerized for reproducible builds and environment parity
- CI/CD via Railway with auto-deploy on git push
- Dual-mode architecture: cloud mode (Groq) and local mode (Ollama + ChromaDB)

---

## 🧱 Tech Stack

| Layer | Technology |
|-------|------------|
| API Framework | FastAPI (Python 3.12) |
| LLM Provider | Groq (Llama 3.3 70B) |
| Rate Limiting | SlowAPI |
| Retry Logic | Tenacity |
| Vector DB (local mode) | ChromaDB |
| Session Memory (local mode) | Redis |
| Local LLM (local mode) | Ollama (phi3:mini) |
| Container | Docker |
| Hosting | Railway |
| CI/CD | GitHub webhook to Railway |

---

## 🏛️ Architecture

Client -> Railway Public Domain -> FastAPI Container (Docker)

Middleware chain in the container:
- Structured Logging Middleware (Request ID, Latency)
- CORS Middleware
- Rate Limiter (SlowAPI)
- Auth Middleware (X-API-Key)
- Global Exception Handler

Request path for /query:
TTL LRU Cache -> Retry Layer -> Groq API

Public endpoints: /health, /diagnose, /cache/stats

Full architecture doc: [docs/architecture.md](docs/architecture.md)

---

## 🔌 API Endpoints

### Public

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Root health message |
| GET | /health | Liveness probe |
| GET | /diagnose | Network/DNS diagnostics |
| GET | /cache/stats | Cache telemetry (size, hits, misses, hit rate) |

### Protected (require X-API-Key header)

| Method | Endpoint | Rate Limit | Description |
|--------|----------|------------|-------------|
| POST | /query | 10/min | Submit a question, get AI-generated answer |
| POST | /upload | 5/min | Upload document (cloud mode: disabled) |
| POST | /cache/clear | — | Admin: clear response cache |

---

## 🚀 Quick Start

### Using The Live API

curl -X POST https://finai-ops-production.up.railway.app/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"question": "What is operational risk?", "top_k": 3}'

### Running Locally (Cloud Mode)

Prerequisites: Docker, Groq API key (free at https://console.groq.com)

git clone https://github.com/Nuamanjaleel/finai-ops.git
cd finai-ops

Set environment variables:
- GEN_MODE=cloud
- GROQ_API_KEY=gsk_your_key_here
- API_KEY=your_random_secret

Build and run:
docker build -t finai-ops .
docker run -p 8000:8000 -e GEN_MODE=cloud -e GROQ_API_KEY=xxx -e API_KEY=xxx finai-ops

Visit http://localhost:8000/docs for the interactive Swagger UI.

---

## 🎯 Design Decisions

### Why Groq over OpenAI/HuggingFace?
- Latency: Groq's LPU architecture delivers ~10x faster inference than GPU providers
- Cost: Free tier (14,400 requests/day) suitable for demos and MVPs
- Compatibility: OpenAI-compatible API enables provider switching without code changes
- HuggingFace deprecation: Free serverless Inference API was deprecated in 2024

### Why In-Memory Cache Instead of Redis (Cloud Mode)?
- Simplicity: No external dependency for cloud deployment
- Sufficient scale: 100-entry cache covers common repeated queries
- Trade-off: Not shared across instances, would need Redis for horizontal scaling

### Why SlowAPI for Rate Limiting?
- Native FastAPI integration with decorator syntax
- Sliding window algorithm (more accurate than fixed-window)
- Per-IP granularity prevents single-user abuse

### Why Tenacity for Retries?
- Industry standard (used by AWS SDK, LangChain)
- Exponential backoff prevents thundering herd
- Selective retry: only on transient failures (5xx), never on 4xx client errors

Full design rationale: [docs/architecture.md](docs/architecture.md)

---

## 🔬 Testing The Live API

### Test Rate Limiting
Send 11 requests within 60 seconds — the 11th returns 429 Too Many Requests.

### Test Cache
Send the same query twice — the second returns "cache": "HIT" with near-zero latency.

### Test Authentication
Omit the X-API-Key header — response returns 401 Unauthorized.

---

## 📁 Project Structure

finai-ops/
- app/
  - main.py (FastAPI app + endpoints)
  - middleware/
    - auth.py (API key validation)
    - rate_limit.py (SlowAPI limiter)
    - logging.py (Structured JSON logging)
  - services/
    - ingestion.py (Groq API integration + retry)
    - cache.py (TTL LRU cache)
- docs/
  - architecture.md (Full system architecture)
- Dockerfile
- requirements.txt
- README.md

---

## 🌟 What Makes This Project Different

Most tutorial projects stop at "it works locally". FinAI Ops demonstrates production readiness:

- Public deployment with real infrastructure
- Every request authenticated, rate-limited, cached, logged
- Automatic recovery from transient failures
- Machine-parseable observability
- Architectural documentation with trade-off analysis

---

## 📬 Contact

Built by Nuaman M
- GitHub: [@Nuamanjaleel](https://github.com/Nuamanjaleel)
- LinkedIn: [Nuaman M](https://www.linkedin.com/in/nuamanjaleel/)
- Email: [nuamanjaleel18@gmail.com](mailto:nuamanjaleel18@gmail.com)

---

## 📄 License

MIT License — see LICENSE file for details.