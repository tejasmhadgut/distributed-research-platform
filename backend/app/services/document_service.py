import httpx
import nltk
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.financial_data import SECFiling
from app.models.document import DocumentChunk
from app.services.embedding_service import embed_text
from html.parser import HTMLParser

EDGAR_HEADERS = {"User-Agent": "research-platform contact@example.com"}
CHUNK_SIZE = 8

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    
    def handle_data(self, data):
        stripped = data.strip()
        if stripped:
            self.parts.append(stripped)

    def get_text(self):
        return " ".join(self.parts)

def _extract_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()

def _chunk_sentences(text: str) -> list[str]:
    sentences = nltk.sent_tokenize(text)
    chunks = []
    for i in range(0, len(sentences), CHUNK_SIZE):
        chunk = " ".join(sentences[i:i + CHUNK_SIZE])
        if chunk.strip():
            chunks.append(chunk)
    return chunks

async def embed_filing(db: AsyncSession, filing: SECFiling, max_chunks: int = 500) -> list[DocumentChunk]:
    if not filing.filing_url:
        return []

    async with httpx.AsyncClient(headers=EDGAR_HEADERS, timeout=60) as client:
        resp = await client.get(filing.filing_url)
        resp.raise_for_status()
        html = resp.text

    text = _extract_text(html)[:300_000]
    chunks = _chunk_sentences(text)[:max_chunks]
    if not chunks:
        return []

    from app.services.embedding_service import _get_model
    import asyncio
    loop = asyncio.get_event_loop()
    model = _get_model()
    vectors = await loop.run_in_executor(None, lambda: model.encode(chunks, batch_size=64, show_progress_bar=False).tolist())

    stored = []
    for idx, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
        chunk = DocumentChunk(
            filing_id=filing.id,
            ticker=filing.ticker,
            chunk_index=idx,
            text=chunk_text,
            embedding=vector,
        )
        db.add(chunk)
        stored.append(chunk)

    await db.commit()
    return stored
