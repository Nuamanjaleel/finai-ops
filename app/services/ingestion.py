import os
import requests

GEN_MODE = os.getenv("GEN_MODE", "cloud")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"


def ingest_document(file_path: str):
    """
    Cloud mode: ingestion disabled (no persistent vector store on free tier).
    Local mode: full RAG pipeline (implemented separately).
    """
    if GEN_MODE == "cloud":
        return {
            "status": "disabled",
            "message": "Ingestion is disabled in cloud mode. Use local deployment for full RAG."
        }

    return {
        "status": "error",
        "message": "Local ingestion pipeline not wired in this build."
    }


def query_documents(question: str, top_k: int = 3):
    if GEN_MODE == "cloud":
        if not HF_API_TOKEN:
            return {
                "question": question,
                "answer": "Error: HF_API_TOKEN not configured."
            }

        headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

        prompt = f"""You are an AI assistant.

Answer the following question clearly and concisely:

Question:
{question}

Answer:
"""

        try:
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{HF_MODEL}",
                headers=headers,
                json={"inputs": prompt},
                timeout=60
            )
            output = response.json()

            if isinstance(output, list):
                answer = output[0].get("generated_text", str(output))
            else:
                answer = str(output)

            return {"question": question, "answer": answer}

        except Exception as e:
            return {"question": question, "answer": f"Error calling HF API: {str(e)}"}

    return {
        "question": question,
        "answer": "Local mode not supported in cloud deployment."
    }
