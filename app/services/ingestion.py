from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb
import uuid
import requests
import os
import json
import re
import redis

# ----------------------------
# Configuration
# ----------------------------

OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_MODEL = "phi3:mini"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

SIMILARITY_THRESHOLD = 1.5
MAX_HISTORY = 6
SESSION_TTL = 3600  # 1 hour

# ----------------------------
# Initialize Services
# ----------------------------

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="finai_docs")

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ----------------------------
# Utility
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


# ----------------------------
# Redis Memory Layer
# ----------------------------

def get_session_key(session_id: str):
    return f"session:{session_id}"


def append_message(session_id: str, role: str, content: str):
    key = get_session_key(session_id)
    message = json.dumps({"role": role, "content": content})
    redis_client.rpush(key, message)
    redis_client.expire(key, SESSION_TTL)


def get_conversation_history(session_id: str):
    if not session_id:
        return ""

    key = get_session_key(session_id)
    messages = redis_client.lrange(key, -MAX_HISTORY*2, -1)

    history = ""
    for msg in messages:
        data = json.loads(msg)
        history += f"{data['role'].capitalize()}: {data['content']}\n"

    return history


# ----------------------------
# Ingestion
# ----------------------------

def ingest_document(file_path: str):
    document_id = str(uuid.uuid4())
    text = extract_text_from_pdf(file_path)
    chunks = chunk_text(text)

    current_week = None

    for index, chunk in enumerate(chunks):
        week_match = re.search(r"WEEK\s+(\d+)", chunk, re.IGNORECASE)
        if week_match:
            current_week = int(week_match.group(1))

        embedding = embedding_model.encode(chunk).tolist()

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
# Retrieval
# ----------------------------

def retrieve_context(question: str, top_k: int = 3):
    query_embedding = embedding_model.encode(question).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=max(top_k * 5, 20)
    )

    retrieved_docs = results["documents"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    week_number = None
    match = re.search(r"Week\s+(\d+)", question, re.IGNORECASE)
    if match:
        week_number = int(match.group(1))

    filtered = []
    for doc, dist, meta in zip(retrieved_docs, distances, metadatas):
        if week_number:
            if meta.get("week") == week_number:
                filtered.append((doc, dist, meta))
        else:
            filtered.append((doc, dist, meta))

    if not filtered:
        filtered = list(zip(retrieved_docs, distances, metadatas))

    filtered = filtered[:top_k]

    docs = [x[0] for x in filtered]
    dists = [x[1] for x in filtered]
    metas = [x[2] for x in filtered]

    if not dists or min(dists) > SIMILARITY_THRESHOLD:
        return None, [], []

    context = "\n\n".join(docs)
    return context, dists, metas


# ----------------------------
# Confidence Scoring
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
# Query
# ----------------------------

def query_documents(question: str, top_k: int = 3, session_id: str = None):

    context, distances, metas = retrieve_context(question, top_k)

    if context is None:
        return {
            "question": question,
            "answer": "No sufficiently relevant context found.",
            "confidence": 0.0
        }

    history = get_conversation_history(session_id)

    prompt = f"""
You are an AI assistant.

Answer using ONLY the context below.

Previous Conversation:
{history}

Context:
{context}

Question:
{question}

Answer:
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    answer = response.json().get("response", "")

    if session_id:
        append_message(session_id, "user", question)
        append_message(session_id, "assistant", answer)

    confidence = compute_confidence(answer, context, distances)

    return {
        "question": question,
        "answer": answer,
        "confidence": confidence,
        "sources": metas
    }

