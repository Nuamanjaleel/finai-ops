import os
import socket
import requests

from app.services.cache import query_cache

GEN_MODE = os.getenv("GEN_MODE", "cloud")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def ingest_document(file_path: str):
    if GEN_MODE == "cloud":
        return {
            "status": "disabled",
            "message": "Ingestion is disabled in cloud mode."
        }
    return {"status": "error", "message": "Local pipeline not wired."}


def diagnose_network():
    results = {}
    for host in ["google.com", "api.groq.com", "huggingface.co"]:
        try:
            ip = socket.gethostbyname(host)
            results[host] = f"✅ Resolved to {ip}"
        except Exception as e:
            results[host] = f"❌ {str(e)}"
    return results


def query_documents(question: str, top_k: int = 3):
    if GEN_MODE != "cloud":
        return {"question": question, "answer": "Local mode not supported."}

    if not GROQ_API_KEY:
        return {"question": question, "answer": "Error: GROQ_API_KEY not configured."}

    # ---- Cache check ----
    cached = query_cache.get(question, top_k)
    if cached is not None:
        return {**cached, "cache": "HIT"}

    # ---- Cache miss: call Groq ----
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are an AI assistant specializing in financial risk and compliance. Provide clear, accurate, and concise answers."
            },
            {"role": "user", "content": question}
        ],
        "max_tokens": 512,
        "temperature": 0.3,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        data = response.json()

        if "choices" in data:
            answer = data["choices"][0]["message"]["content"]
            result = {
                "question": question,
                "answer": answer,
                "model": GROQ_MODEL,
                "provider": "groq",
            }
            # Store in cache
            query_cache.set(question, top_k, result)
            return {**result, "cache": "MISS"}
        else:
            return {
                "question": question,
                "answer": f"Unexpected response: {data}",
                "cache": "MISS",
            }

    except Exception as e:
        return {
            "question": question,
            "answer": f"Error calling Groq API: {str(e)}",
            "cache": "MISS",
        }
