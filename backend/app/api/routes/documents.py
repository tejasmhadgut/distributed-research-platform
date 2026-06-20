from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.core.database import get_db
from app.models.document import DocumentChunk
from app.services.embedding_service import embed_text
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
        {"vec": vector_str, "ticker": input.ticker, "limit": input.limit},
    )
    rows = result.mappings().all()
    return {"results": [dict(r) for r in rows]}
