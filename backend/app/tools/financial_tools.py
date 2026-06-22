from pydantic import BaseModel
from app.tools.registry import tool
from app.services.financial_service import fetch_and_store_metrics
from app.services.edgar_service import fetch_and_store_filings


class TickerInput(BaseModel):
    ticker: str


@tool(
    name="get_company_metrics",
    description="Fetch price history, income statement, and balance sheet for a ticker.",
    input_schema=TickerInput,
)
async def get_company_metrics(input: TickerInput, db) -> dict:
    metrics = await fetch_and_store_metrics(db, input.ticker)
    return {
        "ticker": metrics.ticker,
        "price_data": metrics.price_data,
        "income_statement": metrics.income_statement,
        "balance_sheet": metrics.balance_sheet,
    }


@tool(
    name="search_filings",
    description="Search SEC EDGAR for 10-K filings for a ticker.",
    input_schema=TickerInput,
)
async def search_filings(input: TickerInput, db) -> dict:
    filings = await fetch_and_store_filings(db, input.ticker)
    return {
        "ticker": input.ticker,
        "filings": [
            {"form_type": f.form_type, "filed_at": str(f.filed_at), "filing_url": f.filing_url}
            for f in filings
        ],
    }


@tool(
    name="embed_filings",
    description="Download, chunk, and embed SEC filings into pgvector for a ticker.",
    input_schema=TickerInput,
)
async def embed_filings_tool(input: TickerInput, db) -> dict:
    from sqlalchemy import select
    from app.models.financial_data import SECFiling
    from app.services.document_service import embed_filing
    result = await db.execute(
        select(SECFiling).where(SECFiling.ticker == input.ticker).order_by(SECFiling.id.desc())
    )
    filings = result.scalars().all()
    total = 0
    for filing in filings:
        chunks = await embed_filing(db, filing)
        total += len(chunks)
    return {"ticker": input.ticker, "chunks_stored": total}
