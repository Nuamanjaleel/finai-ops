from fastapi import FastAPI, UploadFile, File, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
import logging

from app.services.ingestion import (
    ingest_document,
    query_documents,
    diagnose_network,
)
from app.middleware.auth import verify_api_key
from app.middleware.rate_limit import limiter

app = FastAPI(
    title="FinAI Ops",
    description="Enterprise-grade AI risk & compliance intelligence system",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/")
def root():
    return {"message": "FinAI Ops backend is running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/diagnose")
def diagnose():
    return diagnose_network()


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
