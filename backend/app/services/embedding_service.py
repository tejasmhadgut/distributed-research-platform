import asyncio
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"
_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


async def embed_text(text: str) -> list[float]:
    loop = asyncio.get_event_loop()
    model = _get_model()
    return await loop.run_in_executor(None, lambda: model.encode(text).tolist())
