import os
import requests

GEN_MODE = os.getenv("GEN_MODE", "cloud")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

def query_documents(question: str, top_k: int = 3):
    if GEN_MODE == "cloud":
        headers = {
            "Authorization": f"Bearer {HF_API_TOKEN}"
        }

        prompt = f"""
You are an AI assistant.

Answer the following question clearly and concisely:

Question:
{question}

Answer:
"""

        response = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers,
            json={"inputs": prompt},
            timeout=60
        )

        output = response.json()

        if isinstance(output, list):
            answer = output[0]["generated_text"]
        else:
            answer = str(output)

        return {
            "question": question,
            "answer": answer
        }

    return {
        "question": question,
        "answer": "Local mode not supported in cloud deployment."
    }
