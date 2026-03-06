from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from schema import TickerSnapshot


@dataclass
class DataQualityResult:
    status: str
    reasons: List[str]


def days_between(d1: Optional[date], d2: Optional[date]) -> Optional[int]:
    if d1 is None or d2 is None:
        return None
    return abs((d1 - d2).days)


def check_required_common_fields(snapshot: TickerSnapshot) -> List[str]:
    missing: List[str] = []

    if not snapshot.ticker:
        missing.append("ticker")
    if not snapshot.company_name:
        missing.append("company_name")
    if snapshot.asof_market is None:
        missing.append("asof_market")
    if snapshot.asof_financial is None:
        missing.append("asof_financial")
    if snapshot.market_cap_jpy is None:
        missing.append("market_cap_jpy")
    if snapshot.avg_daily_value_20d_jpy is None:
        missing.append("avg_daily_value_20d_jpy")
    if snapshot.dividend_yield is None:
        missing.append("dividend_yield")
    if snapshot.annual_dividend_per_share is None:
        missing.append("annual_dividend_per_share")
    if snapshot.annual_dividend_per_share_prev is None:
        missing.append("annual_dividend_per_share_prev")
    if snapshot.payout_ratio is None:
        missing.append("payout_ratio")
    if snapshot.roe is None:
        missing.append("roe")
    if snapshot.years_non_cut_dividend is None:
        missing.append("years_non_cut_dividend")
    if snapshot.years_non_decrease_dividend is None:
        missing.append("years_non_decrease_dividend")
    if snapshot.dividend_cut_count_10y is None:
        missing.append("dividend_cut_count_10y")
    if snapshot.yield_avg_5y is None:
        missing.append("yield_avg_5y")

    return missing


def check_required_non_financial_fields(snapshot: TickerSnapshot) -> List[str]:
    if snapshot.is_financial:
        return []

    missing: List[str] = []

    if snapshot.equity_ratio is None:
        missing.append("equity_ratio")
    if snapshot.operating_cf is None:
        missing.append("operating_cf")
    if snapshot.fcf is None:
        missing.append("fcf")
    if snapshot.net_income is None:
        missing.append("net_income")
    if snapshot.operating_profit is None:
        missing.append("operating_profit")
    if snapshot.ordinary_profit is None:
        missing.append("ordinary_profit")
    if snapshot.years_positive_operating_cf is None:
        missing.append("years_positive_operating_cf")
    if snapshot.years_positive_fcf is None:
        missing.append("years_positive_fcf")

    return missing


def check_minimum_history(snapshot: TickerSnapshot) -> List[str]:
    missing: List[str] = []

    if len(snapshot.eps_5y) < 5:
        missing.append("eps_5y")

    if not snapshot.is_financial:
        if len(snapshot.operating_profit_5y) < 5:
            missing.append("operating_profit_5y")
        if len(snapshot.revenue_5y) < 5:
            missing.append("revenue_5y")

    return missing


def check_data_freshness(
    snapshot: TickerSnapshot,
    today: date,
    market_days_max: int = 5,
    financial_days_warn: int = 365,
    financial_days_invalid: int = 550,
) -> List[str]:
    reasons: List[str] = []

    market_age = days_between(today, snapshot.asof_market)
    financial_age = days_between(today, snapshot.asof_financial)

    if market_age is None:
        reasons.append("missing_market_date")
    elif market_age > market_days_max:
        reasons.append("stale_market_data")

    if financial_age is None:
        reasons.append("missing_financial_date")
    elif financial_age > financial_days_invalid:
        reasons.append("invalid_financial_data")
    elif financial_age > financial_days_warn:
        reasons.append("stale_financial_data")

    return reasons


def evaluate_data_quality(
    snapshot: TickerSnapshot,
    today: date,
    market_days_max: int = 5,
    financial_days_warn: int = 365,
    financial_days_invalid: int = 550,
) -> DataQualityResult:
    reasons: List[str] = []

    missing_common = check_required_common_fields(snapshot)
    if missing_common:
        reasons.extend([f"missing:{x}" for x in missing_common])
        return DataQualityResult(status="SKIPPED", reasons=reasons)

    missing_non_fin = check_required_non_financial_fields(snapshot)
    if missing_non_fin:
        reasons.extend([f"missing:{x}" for x in missing_non_fin])
        return DataQualityResult(status="SKIPPED", reasons=reasons)

    missing_history = check_minimum_history(snapshot)
    if missing_history:
        reasons.extend([f"missing:{x}" for x in missing_history])
        return DataQualityResult(status="SKIPPED", reasons=reasons)

    freshness_reasons = check_data_freshness(
        snapshot=snapshot,
        today=today,
        market_days_max=market_days_max,
        financial_days_warn=financial_days_warn,
        financial_days_invalid=financial_days_invalid,
    )
    reasons.extend(freshness_reasons)

    if any(r == "invalid_financial_data" for r in reasons):
        return DataQualityResult(status="INVALID", reasons=reasons)

    if reasons:
        return DataQualityResult(status="STALE", reasons=reasons)

    return DataQualityResult(status="OK", reasons=[])


def can_new_buy(data_quality: DataQualityResult) -> bool:
    return data_quality.status == "OK"


def can_add_position(data_quality: DataQualityResult) -> bool:
    if data_quality.status == "OK":
        return True

    if data_quality.status != "STALE":
        return False

    allowed_reasons = {"stale_market_data"}
    actual_reasons = set(data_quality.reasons)

    return actual_reasons.issubset(allowed_reasons)


def hold_with_data_issue(data_quality: DataQualityResult) -> bool:
    return data_quality.status in {"STALE", "SKIPPED"}