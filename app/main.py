from fastapi import FastAPI
import requests

app = FastAPI()

OLLAMA_URL = "http://localhost:11434/api/generate"

@app.get("/")
def root():
    return {"message": "FinAI Ops backend is running"}

@app.get("/ask")
def ask_llm(query: str):
    payload = {
        "model": "phi3:mini",
        "prompt": query,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload)
    return {"response": response.json()["response"]}