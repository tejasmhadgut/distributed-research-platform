from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.core.database import get_db
from app.services.embedding_service import embed_text
from app.services.document_service import embed_filing
from app.models.financial_data import SECFiling
from pydantic import BaseModel

router = APIRouter(prefix="/documents", tags=["documents"])


class SearchRequest(BaseModel):
    query: str
    ticker: str
    limit: int = 5


@router.post("/search")
async def search_chunks(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    vector = await embed_text(req.query)
    vector_str = "[" + ",".join(str(v) for v in vector) + "]"
    result = await db.execute(
        text(
            "SELECT id, ticker, chunk_index, text, "
            "1 - (embedding <=> CAST(:vec AS vector)) AS similarity "
            "FROM document_chunks WHERE ticker = :ticker "
            "ORDER BY embedding <=> CAST(:vec AS vector) LIMIT :limit"
        ),
        {"vec": vector_str, "ticker": req.ticker, "limit": req.limit},
    )
    rows = result.mappings().all()
    return {"results": [dict(r) for r in rows]}


class IndexRequest(BaseModel):
    ticker: str


@router.post("/index")
async def index_filings(req: IndexRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    from app.models.document import DocumentChunk

    result = await db.execute(
        select(SECFiling).where(SECFiling.ticker == req.ticker.upper()).order_by(SECFiling.id.desc())
    )
    filings = result.scalars().all()
    if not filings:
        return {"ticker": req.ticker, "chunks_stored": 0, "message": "No filings found. Run a research query first."}

    seen_urls: set[str] = set()
    total = 0
    for filing in filings[:1]:
        if not filing.filing_url or filing.filing_url in seen_urls:
            continue
        seen_urls.add(filing.filing_url)
        existing = await db.execute(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.filing_id == filing.id)
        )
        if existing.scalar() > 0:
            continue
        chunks = await embed_filing(db, filing, max_chunks=500)
        total += len(chunks)

    return {"ticker": req.ticker, "chunks_stored": total}
