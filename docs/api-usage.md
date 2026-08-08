# FinAI Ops — API Usage Guide

Complete examples for consuming the FinAI Ops API in various languages and tools.

**Base URL:** `https://finai-ops-production.up.railway.app`

---

## Authentication

All protected endpoints require the `X-API-Key` header.
X-API-Key: zdMwJPjoTLFPpfRUcIY_W5s4GtEckkZ0xpAo0ZRP8R8


Contact the maintainer to request an API key, or run your own instance and set the `API_KEY` environment variable.

---

## Endpoint Reference

### Public Endpoints (no auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root health check |
| GET | `/health` | Liveness probe |
| GET | `/diagnose` | Network/DNS diagnostics |
| GET | `/cache/stats` | Cache telemetry |

### Protected Endpoints (require X-API-Key)

| Method | Endpoint | Rate Limit | Description |
|--------|----------|------------|-------------|
| POST | `/query` | 10/min per IP | Submit question, get AI answer |
| POST | `/upload` | 5/min per IP | Upload document (cloud mode: disabled) |
| POST | `/cache/clear` | — | Admin: clear response cache |

---

## Examples

### 1. Health Check (Public)

**curl:**
```bash
curl https://finai-ops-production.up.railway.app/health