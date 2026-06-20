import asyncio
import ollama as ol

EMBED_MODEL = "nomic-embed-text"


async def embed_text(text: str) -> list[float]:
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, lambda: ol.embeddings(model=EMBED_MODEL, prompt=text)
    )
    return response["embedding"]
