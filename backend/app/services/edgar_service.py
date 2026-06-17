import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.financial_data import SECFiling

EDGAR_HEADERS = {"User-Agent": "research-platform contact@example.com"}


async def fetch_and_store_filings(
    db: AsyncSession, ticker: str, form_type: str = "10-K", limit: int = 3
) -> list[SECFiling]:
    async with httpx.AsyncClient(headers=EDGAR_HEADERS, timeout=30) as client:
        resp = await client.get(
            f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms={form_type}&dateRange=custom&startdt=2020-01-01"
        )
        resp.raise_for_status()
        data = resp.json()

    hits = data.get("hits", {}).get("hits", [])[:limit]
    filings = []

    for hit in hits:
        source = hit.get("_source", {})
        filing = SECFiling(
            ticker=ticker.upper(),
            form_type=form_type,
            filed_at=source.get("file_date"),
            accession_number=source.get("accession_no"),
            filing_url=f"https://www.sec.gov/Archives/edgar/data/{source.get('ciks', [''])[0]}/{source.get('accession_no', '').replace('-', '')}" if source.get('accession_no') else None,
            raw=source
        )
        db.add(filing)
        await db.commit()
        await db.refresh(filing)
        filings.append(filing)

    return filings
