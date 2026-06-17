import asyncio
import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.financial_data import CompanyMetrics


def _fetch_yfinance(ticker: str) -> dict:
    import time
    stock = yf.Ticker(ticker)

    hist = stock.history(period="1mo")
    price_data = {
        "history": hist.reset_index().to_dict(orient="records") if not hist.empty else []
    }
    time.sleep(2)

    try:
        fast = stock.fast_info
        price_data.update({
            "current_price": fast.get("lastPrice"),
            "market_cap": fast.get("marketCap"),
            "52w_high": fast.get("yearHigh"),
            "52w_low": fast.get("yearLow"),
        })
        info = dict(fast)
    except Exception:
        info = {}
    time.sleep(2)

    try:
        income_stmt = stock.income_stmt
        income_data = income_stmt.to_dict() if income_stmt is not None and not income_stmt.empty else {}
    except Exception:
        income_data = {}
    time.sleep(2)

    try:
        balance = stock.balance_sheet
        balance_data = balance.to_dict() if balance is not None and not balance.empty else {}
    except Exception:
        balance_data = {}

    return {
        "price_data": price_data,
        "income_data": income_data,
        "balance_data": balance_data,
        "raw": info
    }


async def fetch_and_store_metrics(db: AsyncSession, ticker: str) -> CompanyMetrics:
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _fetch_yfinance, ticker)

    metrics = CompanyMetrics(
        ticker=ticker.upper(),
        price_data=data["price_data"],
        income_statement=data["income_data"],
        balance_sheet=data["balance_data"],
        raw=data["raw"]
    )
    db.add(metrics)
    await db.commit()
    await db.refresh(metrics)
    return metrics
