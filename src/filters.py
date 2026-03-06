from __future__ import annotations

from dataclasses import dataclass
from typing import List

from schema import TickerSnapshot


@dataclass
class FilterResult:
    exclude_reasons: List[str]
    caution_score: int
    caution_reasons: List[str]


def check_exclude(snapshot: TickerSnapshot) -> List[str]:
    reasons: List[str] = []

    if not snapshot.is_active:
        reasons.append("inactive_watchlist")

    if snapshot.dividend_yield is not None and snapshot.dividend_yield < 0.035:
        reasons.append("below_min_dividend_yield")

    if snapshot.market_cap_jpy is not None and snapshot.market_cap_jpy < 10_000_000_000:
        reasons.append("below_min_market_cap")

    if (
        snapshot.avg_daily_value_20d_jpy is not None
        and snapshot.avg_daily_value_20d_jpy < 50_000_000
    ):
        reasons.append("below_min_liquidity")

    if (
        snapshot.annual_dividend_per_share is not None
        and snapshot.annual_dividend_per_share_prev is not None
        and snapshot.annual_dividend_per_share < snapshot.annual_dividend_per_share_prev
    ):
        reasons.append("recent_dividend_cut")

    if snapshot.has_exclude_keyword:
        reasons.append("exclude_keyword_detected")

    if snapshot.gap_down_ratio is not None and snapshot.gap_down_ratio <= -0.15:
        reasons.append("severe_gap_down_after_earnings")

    if snapshot.is_financial:
        if snapshot.payout_ratio is not None and snapshot.payout_ratio > 1.0:
            reasons.append("payout_ratio_too_high_financial")
    else:
        if snapshot.payout_ratio is not None and snapshot.payout_ratio > 1.0:
            reasons.append("payout_ratio_too_high")

        if snapshot.equity_ratio is not None and snapshot.equity_ratio < 0.20:
            reasons.append("equity_ratio_too_low")

    return reasons


def compute_caution_score(snapshot: TickerSnapshot, data_quality_status: str) -> tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []

    def add(points: int, reason: str) -> None:
        nonlocal score
        score += points
        reasons.append(reason)

    if snapshot.is_financial:
        if snapshot.payout_ratio is not None and snapshot.payout_ratio > 0.85:
            add(1, "high_payout_ratio_financial")

        if snapshot.roe is not None and snapshot.roe < 0.05:
            add(1, "low_roe_financial")

        if snapshot.years_non_cut_dividend is not None and snapshot.years_non_cut_dividend < 3:
            add(1, "short_non_cut_history_financial")

    else:
        if snapshot.payout_ratio is not None and snapshot.payout_ratio > 0.80:
            add(1, "high_payout_ratio")

        if snapshot.roe is not None and snapshot.roe < 0.05:
            add(1, "low_roe")

        if (
            snapshot.operating_cf is not None
            and snapshot.net_income is not None
            and snapshot.net_income > 0
            and snapshot.operating_cf < snapshot.net_income
        ):
            add(1, "ocf_below_net_income")

        if (
            snapshot.years_positive_fcf is not None
            and snapshot.years_positive_fcf < 2
        ):
            add(1, "weak_fcf_history")

    if snapshot.has_caution_keyword:
        add(2, "caution_keyword_detected")

    if snapshot.gap_down_ratio is not None and snapshot.gap_down_ratio <= -0.08:
        add(2, "earnings_gap_down")

    if snapshot.abnormal_volume_down_flag:
        add(1, "abnormal_volume_down")

    if data_quality_status == "STALE":
        add(1, "stale_data")

    return score, reasons


def evaluate_filters(snapshot: TickerSnapshot, data_quality_status: str) -> FilterResult:
    exclude_reasons = check_exclude(snapshot)
    caution_score, caution_reasons = compute_caution_score(snapshot, data_quality_status)

    return FilterResult(
        exclude_reasons=exclude_reasons,
        caution_score=caution_score,
        caution_reasons=caution_reasons,
    )