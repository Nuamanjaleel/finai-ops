import os
import socket
import requests

GEN_MODE = os.getenv("GEN_MODE", "cloud")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "meta-llama/Llama-3.2-3B-Instruct")


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
    for host in ["google.com", "router.huggingface.co", "huggingface.co"]:
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

    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json",
    }

    # Use HF Inference Providers chat completions API (OpenAI-compatible)
    url = "https://router.huggingface.co/v1/chat/completions"

    payload = {
        "model": HF_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are an AI assistant specializing in financial risk and compliance. Answer clearly and concisely."
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "max_tokens": 512,
        "temperature": 0.3,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        data = response.json()

        if "choices" in data:
            answer = data["choices"][0]["message"]["content"]
        else:
            answer = f"Unexpected response: {data}"

        return {
            "question": question,
            "answer": answer,
            "model": HF_MODEL,
        }

    except Exception as e:
        return {"question": question, "answer": f"Error calling HF API: {str(e)}"}
