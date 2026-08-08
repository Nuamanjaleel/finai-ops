from fastapi import FastAPI, UploadFile, File, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
import sys
import logging
import json

from app.services.ingestion import (
    ingest_document,
    query_documents,
    diagnose_network,
)
from app.services.cache import query_cache
from app.middleware.auth import verify_api_key
from app.middleware.rate_limit import limiter
from app.middleware.logging import StructuredLoggingMiddleware


# ----------------------------
# JSON Logging Setup
# ----------------------------

class JSONFormatter(logging.Formatter):
    def format(self, record):
        try:
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, ValueError):
            return json.dumps({
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            })


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]

logger = logging.getLogger("finai-ops")


# ----------------------------
# App Setup
# ----------------------------

app = FastAPI(
    title="FinAI Ops",
    description="Enterprise-grade AI risk & compliance intelligence system",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(StructuredLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------
# Global Exception Handler
# ----------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches any unhandled exception and returns a clean JSON error
    with request_id for tracing. Never leaks stack traces to clients.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(f"Unhandled exception on {request.url.path} [request_id={request_id}]")

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please contact support with the request_id.",
            "request_id": request_id,
        },
    )


# ----------------------------
# Public Endpoints
# ----------------------------

@app.get("/")
def root():
    return {"message": "FinAI Ops backend is running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/diagnose")
def diagnose():
    return diagnose_network()


@app.get("/cache/stats")
def cache_stats():
    return query_cache.stats()


# ----------------------------
# Admin Endpoint
# ----------------------------

@app.post("/cache/clear", dependencies=[Depends(verify_api_key)])
def cache_clear():
    query_cache.clear()
    return {"status": "cache cleared"}


# ----------------------------
# Protected Endpoints
# ----------------------------

@app.post("/upload", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def upload_document(request: Request, file: UploadFile = File(...)):
    file_location = f"temp_{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    result = ingest_document(file_location)
    os.remove(file_location)
    return result


class QueryRequest(BaseModel):
    question: str
    top_k: int = 3


@app.post("/query", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
def query(request: Request, payload: QueryRequest):
    return query_documents(
        question=payload.question,
        top_k=payload.top_k
    )
