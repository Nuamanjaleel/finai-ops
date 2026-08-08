import os
import socket
import logging
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.services.cache import query_cache

logger = logging.getLogger("finai-ops")

GEN_MODE = os.getenv("GEN_MODE", "cloud")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class UpstreamAPIError(Exception):
    """Raised when upstream LLM API returns an error."""
    pass


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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((requests.exceptions.RequestException, UpstreamAPIError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_groq(payload: dict) -> dict:
    """
    Calls Groq API with automatic retry on transient failures.
    Retries: 3 attempts, exponential backoff (1s, 2s, 4s max).
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)

    # Retry on 5xx server errors
    if response.status_code >= 500:
        raise UpstreamAPIError(f"Groq returned {response.status_code}: {response.text}")

    data = response.json()

    if "choices" not in data:
        # 4xx errors — do NOT retry (client error)
        raise ValueError(f"Groq API error: {data}")

    return data


def query_documents(question: str, top_k: int = 3):
    if GEN_MODE != "cloud":
        return {"question": question, "answer": "Local mode not supported."}

    if not GROQ_API_KEY:
        return {"question": question, "answer": "Error: GROQ_API_KEY not configured."}

    # ---- Cache check ----
    cached = query_cache.get(question, top_k)
    if cached is not None:
        return {**cached, "cache": "HIT"}

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
        data = _call_groq(payload)
        answer = data["choices"][0]["message"]["content"]

        result = {
            "question": question,
            "answer": answer,
            "model": GROQ_MODEL,
            "provider": "groq",
        }
        query_cache.set(question, top_k, result)
        return {**result, "cache": "MISS"}

    except UpstreamAPIError as e:
        logger.error(f"Upstream API failed after retries: {e}")
        return {
            "question": question,
            "answer": "Upstream LLM service is temporarily unavailable. Please try again shortly.",
            "cache": "MISS",
            "error": "upstream_unavailable",
        }
    except ValueError as e:
        logger.error(f"Invalid Groq response: {e}")
        return {
            "question": question,
            "answer": "Request failed due to invalid parameters or model error.",
            "cache": "MISS",
            "error": "invalid_request",
        }
    except Exception as e:
        logger.exception("Unexpected error in query_documents")
        return {
            "question": question,
            "answer": "An unexpected error occurred. Please try again.",
            "cache": "MISS",
            "error": "internal_error",
        }
