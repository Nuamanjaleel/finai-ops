# FinAI Ops — System Architecture

## Overview

FinAI Ops is a production-grade GenAI backend for financial risk and compliance intelligence. It exposes a REST API that accepts natural language questions and returns AI-generated answers using Groq's high-speed LLM inference.

## High-Level Architecture

Client → Railway Public Domain → FastAPI Container → Groq LLM API

The container includes multiple middleware layers:

1. **Structured Logging Middleware** — assigns request IDs, tracks latency, logs in JSON
2. **CORS Middleware** — handles cross-origin requests
3. **Rate Limiter (SlowAPI)** — 10 req/min per IP for /query, 5 req/min for /upload
4. **Authentication Middleware** — validates X-API-Key header on protected endpoints
5. **TTL LRU Cache** — 100-entry cache with 1-hour TTL for repeated queries
6. **Retry Layer (Tenacity)** — exponential backoff on transient Groq API failures
7. **Global Exception Handler** — catches all unhandled errors, returns clean JSON

## Endpoints

### Public (no auth required)
- `GET /` — Root health message
- `GET /health` — Liveness probe
- `GET /diagnose` — Network/DNS diagnostics
- `GET /cache/stats` — Cache hit/miss telemetry

### Protected (require X-API-Key header)
- `POST /query` — Submit a question, get AI-generated answer
- `POST /upload` — Upload document (cloud mode: disabled stub)
- `POST /cache/clear` — Admin: clear the response cache

## Request Flow

1. Client sends `POST /query` with `X-API-Key` header and JSON body
2. Logging middleware assigns a UUID request ID and starts latency timer
3. Auth middleware validates the API key (401 if missing/invalid)
4. Rate limiter checks per-IP quota (429 if exceeded)
5. Cache is checked for existing response (cache HIT returns instantly)
6. On cache MISS, Groq API is called with exponential backoff retry
7. Response is cached and returned with `X-Request-ID` header

## Design Decisions

### Why Groq over OpenAI/HuggingFace?
- **Latency**: Groq LPU delivers ~10x faster inference than GPU providers
- **Cost**: Free tier (14,400 requests/day) suitable for demos and MVPs
- **Compatibility**: OpenAI-compatible API enables easy provider switching
- **HuggingFace deprecation**: Free serverless Inference API was deprecated in 2024

### Why In-Memory Cache Instead of Redis?
- **Simplicity**: No external dependency for cloud deployment
- **Sufficient scale**: 100-entry cache covers common repeated queries
- **Trade-off**: Not shared across instances — would need Redis for horizontal scaling

### Why SlowAPI for Rate Limiting?
- Native FastAPI integration with decorator-based syntax
- Sliding window algorithm for accurate limiting
- Per-IP granularity prevents single-user abuse

### Why Tenacity for Retries?
- Industry standard, used by AWS SDK and LangChain
- Exponential backoff prevents thundering herd on upstream recovery
- Selective retry only on transient failures (5xx, network), never on 4xx client errors

### Why Structured JSON Logging?
- Machine-parseable format compatible with Datadog, Splunk, CloudWatch
- Correlation IDs enable distributed tracing readiness
- Latency tracking enables SLA monitoring and p99 analysis

## Environment Modes

| Mode  | Vector DB | LLM              | Memory          | Use Case              |
|-------|-----------|------------------|-----------------|------------------------|
| cloud | None      | Groq API         | In-memory cache | Public demo / Railway |
| local | ChromaDB  | Ollama phi3:mini | Redis           | Full RAG pipeline     |

## Deployment Pipeline

Local Development (WSL) → git push → GitHub → Railway Webhook → Docker Build → Container Registry → Production Runtime (1GB RAM, 2 vCPU)

## Technology Stack

- **Backend**: FastAPI (Python 3.12)
- **LLM**: Groq (Llama 3.3 70B)
- **Rate Limiting**: SlowAPI
- **Retries**: Tenacity
- **Container**: Docker
- **Hosting**: Railway
- **Version Control**: Git + GitHub