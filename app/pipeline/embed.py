import requests

OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL_NAME = "nomic-embed-text"

def generate_embedding(text: str) -> list:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": text
        }
    )

    if response.status_code != 200:
        raise Exception(f"Ollama error: {response.text}")

    return response.json()["embedding"]