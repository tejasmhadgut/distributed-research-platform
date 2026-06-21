import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.financial_data import SECFiling
from app.core.cache import cache_delete
from app.core.cache_decorator import cached
from app.models.financial_data import SECFiling
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

EDGAR_HEADERS = {"User-Agent": "research-platform contact@example.com"}
_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


async def _get_cik(client: httpx.AsyncClient, ticker: str) -> str | None:
    resp = await client.get(_COMPANY_TICKERS_URL)
    resp.raise_for_status()
    data = resp.json()
    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry.get("ticker", "").upper() == ticker_upper:
            return str(entry["cik_str"]).zfill(10)
    return None


async def fetch_and_store_filings(
    db: AsyncSession, ticker: str, form_type: str = "10-K", limit: int = 3
) -> list[SECFiling]:
    async with httpx.AsyncClient(headers=EDGAR_HEADERS, timeout=30) as client:
        cik = await _get_cik(client, ticker)
        if not cik:
            return []

        resp = await client.get(f"https://data.sec.gov/submissions/CIK{cik}.json")
        resp.raise_for_status()
        submissions = resp.json()

    recent = submissions.get("filings", {}).get("recent", {})
    accession_numbers = recent.get("accessionNumber", [])
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])

    filings = []
    for accession_no, form, date, doc in zip(accession_numbers, forms, dates, primary_docs):
        if form != form_type:
            continue
        if len(filings) >= limit:
            break

        accession_no_clean = accession_no.replace("-", "")
        filing_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{int(cik)}/{accession_no_clean}/{doc}"
        )

        filing = SECFiling(
            ticker=ticker.upper(),
            form_type=form_type,
            filed_at=date,
            accession_number=accession_no,
            filing_url=filing_url,
            raw={"cik": cik, "primary_document": doc},
        )
        db.add(filing)
        await db.commit()
        await db.refresh(filing)
        filings.append(filing)
    await cache_delete(f"filings:{ticker.upper()}:{form_type}")
    return filings


@cached(key_fn=lambda db, ticker, form_type="10-K": f"filings:{ticker.upper()}:{form_type}", ttl=86400)
async def get_cached_filings(db: AsyncSession, ticker: str, form_type: str = "10-K") -> list | None:
    result = await db.execute(
        select(SECFiling)
        .where(SECFiling.ticker == ticker.upper(), SECFiling.form_type == form_type)
        .order_by(desc(SECFiling.fetched_at))
        .limit(5)
    )
    rows = result.scalars().all()
    if not rows:
        return None
    return [
        {
            "id": r.id,
            "ticker": r.ticker,
            "form_type": r.form_type,
            "filed_at": r.filed_at,
            "filing_url": r.filing_url,
        }
        for r in rows
    ]
