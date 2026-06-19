from pydantic import BaseModel
from app.tools.registry import tool
from app.services.embedding_service import embed_text
from sqlalchemy import text


class SearchInput(BaseModel):
    query: str
    ticker: str
    limit: int = 5


@tool(
    name="search_document_chunks",
    description="Semantic search over embedded SEC filing chunks for a ticker using a natural language query.",
    input_schema=SearchInput,
)
async def search_document_chunks(input: SearchInput, db) -> dict:
    vector = await embed_text(input.query)
    vector_str = "[" + ",".join(str(v) for v in vector) + "]"
    result = await db.execute(
        text(
            "SELECT id, ticker, chunk_index, text, "
            "1 - (embedding <=> :vec::vector) AS similarity "
            "FROM document_chunks WHERE ticker = :ticker "
            "ORDER BY embedding <=> :vec::vector LIMIT :limit"
        ),
        {"vec": vector_str, "ticker": input.ticker, "limit": input.limit},
    )
    rows = result.mappings().all()
    return {"results": [dict(r) for r in rows]}
