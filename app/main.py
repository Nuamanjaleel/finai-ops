from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging

from app.services.ingestion import (
    ingest_document,
    query_documents
)

app = FastAPI()

# ----------------------------
# CORS
# ----------------------------

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
# Health Check
# ----------------------------

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {"message": "FinAI Ops backend is running"}

# ----------------------------
# Upload Endpoint
# ----------------------------

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    file_location = f"temp_{file.filename}"

    with open(file_location, "wb") as f:
        f.write(await file.read())

    result = ingest_document(file_location)

    os.remove(file_location)

    return result

# ----------------------------
# Query Model
# ----------------------------

class QueryRequest(BaseModel):
    question: str
    top_k: int = 3

# ----------------------------
# Query Endpoint
# ----------------------------

@app.post("/query")
def query(request: QueryRequest):
    return query_documents(
        question=request.question,
        top_k=request.top_k
    )
