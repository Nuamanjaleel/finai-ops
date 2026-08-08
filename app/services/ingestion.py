import os
import socket
import requests

GEN_MODE = os.getenv("GEN_MODE", "cloud")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"


def ingest_document(file_path: str):
    if GEN_MODE == "cloud":
        return {
            "status": "disabled",
            "message": "Ingestion is disabled in cloud mode."
        }
    return {"status": "error", "message": "Local pipeline not wired."}


def diagnose_network():
    """Test DNS + connectivity from container."""
    results = {}
    for host in ["google.com", "api-inference.huggingface.co", "router.huggingface.co", "huggingface.co"]:
        try:
            ip = socket.gethostbyname(host)
            results[host] = f"✅ Resolved to {ip}"
        except Exception as e:
            results[host] = f"❌ {str(e)}"
    return results


def query_documents(question: str, top_k: int = 3):
    if GEN_MODE != "cloud":
        return {"question": question, "answer": "Local mode not supported."}

    if not HF_API_TOKEN:
        return {"question": question, "answer": "Error: HF_API_TOKEN not configured."}

    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

    prompt = f"""You are an AI assistant.

Answer the following question clearly and concisely:

Question:
{question}

Answer:
"""

    # Try new HF router endpoint first, fall back to old
    endpoints = [
        f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}",
        f"https://api-inference.huggingface.co/models/{HF_MODEL}",
    ]

    last_error = None
    for url in endpoints:
        try:
            response = requests.post(
                url,
                headers=headers,
                json={"inputs": prompt},
                timeout=60
            )
            output = response.json()

            if isinstance(output, list):
                answer = output[0].get("generated_text", str(output))
            else:
                answer = str(output)

            return {"question": question, "answer": answer, "endpoint": url}

        except Exception as e:
            last_error = f"{url} -> {str(e)}"
            continue

    return {"question": question, "answer": f"All endpoints failed. Last error: {last_error}"}
