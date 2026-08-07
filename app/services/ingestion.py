from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb
import uuid
import requests
import os
import json
import re

# ----------------------------
# CONFIG
# ----------------------------

GEN_MODE = os.getenv("GEN_MODE", "local")

HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = "phi3:mini"

SIMILARITY_THRESHOLD = 1.5

# ----------------------------
# INIT
# ----------------------------

embedding_model = None

def get_embedding_model():
    global embedding_model
    if embedding_model is None:
        embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return embedding_model

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="finai_docs")

# ----------------------------
# PDF INGESTION
# ----------------------------

def extract_text_from_pdf(file_path: str):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def ingest_document(file_path: str):
    document_id = str(uuid.uuid4())
    text = extract_text_from_pdf(file_path)
    chunks = chunk_text(text)

    current_week = None

    for index, chunk in enumerate(chunks):
        week_match = re.search(r"WEEK\s+(\d+)", chunk, re.IGNORECASE)
        if week_match:
            current_week = int(week_match.group(1))

        embedding = get_embedding_model().encode(chunk).tolist()

        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[str(uuid.uuid4())],
            metadatas=[{
                "document_id": document_id,
                "week": current_week,
                "chunk_index": index
            }]
        )

    return {
        "status": "Document ingested",
        "document_id": document_id,
        "chunks": len(chunks)
    }

# ----------------------------
# RETRIEVAL
# ----------------------------

def retrieve_context(question: str, top_k: int = 3):

    query_embedding = get_embedding_model().encode(question).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=max(top_k * 5, 20)
    )

    docs = results["documents"][0]
    distances = results["distances"][0]
    metas = results["metadatas"][0]

    week_number = None
    match = re.search(r"Week\s+(\d+)", question, re.IGNORECASE)
    if match:
        week_number = int(match.group(1))

    filtered = []
    for doc, dist, meta in zip(docs, distances, metas):
        if week_number:
            if meta.get("week") == week_number:
                filtered.append((doc, dist, meta))
        else:
            filtered.append((doc, dist, meta))

    if not filtered:
        filtered = list(zip(docs, distances, metas))

    filtered = filtered[:top_k]

    docs = [x[0] for x in filtered]
    dists = [x[1] for x in filtered]
    metas = [x[2] for x in filtered]

    if not dists or min(dists) > SIMILARITY_THRESHOLD:
        return None, [], []

    context = "\n\n".join(docs)
    return context, dists, metas

# ----------------------------
# INFERENCE
# ----------------------------

def generate_answer(prompt: str):

    if GEN_MODE == "cloud":
        headers = {
            "Authorization": f"Bearer {HF_API_TOKEN}"
        }

        response = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers,
            json={"inputs": prompt},
            timeout=60
        )

        output = response.json()

        if isinstance(output, list):
            return output[0]["generated_text"]

        return str(output)

    else:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
        )

        return response.json().get("response", "")

# ----------------------------
# CONFIDENCE
# ----------------------------

def compute_confidence(answer: str, context: str, distances: list):
    if not context:
        return 0.0

    best_distance = min(distances) if distances else 2.0
    retrieval_conf = max(0.0, 1 - (best_distance / 2))

    answer_tokens = set(answer.lower().split())
    context_tokens = set(context.lower().split())

    overlap = len(answer_tokens.intersection(context_tokens))
    overlap_score = overlap / len(answer_tokens) if answer_tokens else 0

    confidence = 0.6 * retrieval_conf + 0.4 * overlap_score
    return round(confidence, 3)

# ----------------------------
# QUERY
# ----------------------------

def query_documents(question: str, top_k: int = 3):

    context, distances, metas = retrieve_context(question, top_k)

    if context is None:
        return {
            "question": question,
            "answer": "No relevant context found.",
            "confidence": 0.0
        }

    prompt = f"""
You are an AI assistant.

Answer using ONLY the context below.

Context:
{context}

Question:
{question}

Answer:
"""

    answer = generate_answer(prompt)

    confidence = compute_confidence(answer, context, distances)

    return {
        "question": question,
        "answer": answer,
        "confidence": confidence,
        "sources": metas
    }
