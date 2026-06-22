import asyncio
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.financial_data import CompanyMetrics
from app.core.cache import cache_delete
from app.core.cache_decorator import cached


def _get_statement_value(data: pd.DataFrame, row_name: str) -> float | None:
    row = data[data['Breakdown'] == row_name]
    if row.empty:
        return None
    date_cols = sorted([c for c in data.columns if c != 'Breakdown'], reverse=True)
    if not date_cols:
        return None
    val = row.iloc[0][date_cols[0]]
    if val == '*' or pd.isna(val):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _fetch_defeatbeta(ticker: str) -> dict:
    from defeatbeta_api.data.ticker import Ticker
    t = Ticker(ticker.upper())

    price_df = t.price()
    price_df = price_df.sort_values('report_date')
    recent = price_df.tail(252)

    current_price = float(price_df.iloc[-1]['close']) if not price_df.empty else None
    week52_high = float(recent['high'].max()) if not recent.empty else None
    week52_low = float(recent['low'].min()) if not recent.empty else None

    market_cap_df = t.market_capitalization()
    market_cap = float(market_cap_df.iloc[-1]['market_capitalization']) if not market_cap_df.empty else None

    pe_df = t.ttm_pe()
    pe_ratio = float(pe_df.iloc[-1]['ttm_pe']) if not pe_df.empty else None

    inc_data = t.annual_income_statement().data
    total_revenue = _get_statement_value(inc_data, 'Total Revenue')
    net_income = _get_statement_value(inc_data, 'Net Income Common Stockholders')

    bal_data = t.annual_balance_sheet().data
    total_assets = _get_statement_value(bal_data, 'Total Assets')
    total_debt = _get_statement_value(bal_data, 'Total Debt')

    return {
        "price_data": {
            "current_price": current_price,
            "fifty_two_week_high": week52_high,
            "fifty_two_week_low": week52_low,
            "pe_ratio": pe_ratio,
            "market_cap": market_cap,
        },
        "income_data": {
            "total_revenue": total_revenue,
            "net_income": net_income,
        },
        "balance_data": {
            "total_assets": total_assets,
            "total_debt": total_debt,
        },
        "raw": {}
    }


async def fetch_and_store_metrics(db: AsyncSession, ticker: str) -> CompanyMetrics:
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _fetch_defeatbeta, ticker)

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
    await cache_delete(f"metrics:{ticker.upper()}")
    return metrics


@cached(key_fn=lambda db, ticker: f"metrics:{ticker.upper()}", ttl=3600)
async def get_cached_metrics(db: AsyncSession, ticker: str) -> dict | None:
    result = await db.execute(
        select(CompanyMetrics)
        .where(CompanyMetrics.ticker == ticker.upper())
        .order_by(desc(CompanyMetrics.fetched_at))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return {
        "ticker": row.ticker,
        "fetched_at": str(row.fetched_at),
        "price_data": row.price_data,
        "income_statement": row.income_statement,
        "balance_sheet": row.balance_sheet,
    }
