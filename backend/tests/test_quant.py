import pytest
from app.services.quant_service import _compute_metrics


class _FakeRow:
    def __init__(self, price_data, income_statement, balance_sheet):
        self.price_data = price_data
        self.income_statement = income_statement
        self.balance_sheet = balance_sheet


def test_compute_metrics_full():
    row = _FakeRow(
        price_data={
            "current_price": 213.55,
            "fifty_two_week_high": 260.10,
            "fifty_two_week_low": 169.21,
            "pe_ratio": 32.8,
            "market_cap": 3_200_000_000_000,
        },
        income_statement={"total_revenue": 391_035_000_000, "net_income": 93_736_000_000},
        balance_sheet={"total_assets": 364_980_000_000, "total_debt": 101_304_000_000},
    )
    metrics = _compute_metrics(row)

    assert metrics["cap_tier"] == "mega"
    assert metrics["pe_ratio"] == 32.8
    assert 0.23 < metrics["net_margin"] < 0.25
    assert 0.27 < metrics["debt_to_assets"] < 0.29
    assert metrics["price_vs_52w_high"] < 0
    assert metrics["volatility_proxy"] > 0


def test_compute_metrics_missing_fields():
    row = _FakeRow(price_data={}, income_statement={}, balance_sheet={})
    metrics = _compute_metrics(row)
    assert metrics == {}


def test_compute_metrics_mid_cap():
    row = _FakeRow(
        price_data={"market_cap": 5_000_000_000},
        income_statement={},
        balance_sheet={},
    )
    metrics = _compute_metrics(row)
    assert metrics["cap_tier"] == "mid"


def test_compute_metrics_small_cap():
    row = _FakeRow(
        price_data={"market_cap": 500_000_000},
        income_statement={},
        balance_sheet={},
    )
    metrics = _compute_metrics(row)
    assert metrics["cap_tier"] == "small"
