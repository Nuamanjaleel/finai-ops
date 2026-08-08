from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging

from app.services.ingestion import (
    ingest_document,
    query_documents,
    diagnose_network,
)
from app.middleware.auth import verify_api_key

app = FastAPI(
    title="FinAI Ops",
    description="Enterprise-grade AI risk & compliance intelligence system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ----------------------------
# Public Endpoints (no auth)
# ----------------------------

@app.get("/")
def root():
    return {"message": "FinAI Ops backend is running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/diagnose")
def diagnose():
    """Diagnostic endpoint for network/DNS testing."""
    return diagnose_network()


# ----------------------------
# Protected Endpoints (require X-API-Key)
# ----------------------------

@app.post("/upload", dependencies=[Depends(verify_api_key)])
async def upload_document(file: UploadFile = File(...)):
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
def query(request: QueryRequest):
    return query_documents(
        question=request.question,
        top_k=request.top_k
    )
