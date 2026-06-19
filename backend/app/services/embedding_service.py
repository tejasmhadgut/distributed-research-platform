import httpx

OLLAMA_URL = "https://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"

async def embed_text(text:str) -> list[float]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp =await client.post(OLLAMA_URL, json={"model":EMBED_MODEL, "prompt":"text"})
        resp.raise_for_status()
        return resp.json()["embedding"]