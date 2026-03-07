from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import List

from schema import TickerSnapshot


@dataclass
class ScoreResult:
    score_dividend_stability: int
    score_financial_soundness: int
    score_cashflow_soundness: int
    score_earnings_stability: int
    score_shareholder_policy: int
    score_yield_overheat: int
    score_sector_adjustment: int
    total_score: int


def calc_cv_and_declines(values: List[float]) -> tuple[float, int, int]:
    if len(values) < 2:
        return math.inf, 999, 999

    mu = statistics.mean(values)
    if abs(mu) < 1e-6:
        cv = math.inf
    else:
        sigma = statistics.pstdev(values)
        cv = sigma / abs(mu)

    decline_count = 0
    negative_count = 0

    for i, v in enumerate(values):
        if v <= 0:
            negative_count += 1
        if i > 0 and values[i] < values[i - 1]:
            decline_count += 1

    return cv, decline_count, negative_count


def score_series(values: List[float], high_score: int, medium_score: int) -> int:
    cv, decline_count, negative_count = calc_cv_and_declines(values)

    if cv < 0.15 and decline_count == 0 and negative_count == 0:
        return high_score

    if cv < 0.30 and decline_count <= 1 and negative_count == 0:
        return medium_score

    return 0


def compute_dividend_stability_score(snapshot: TickerSnapshot) -> int:
    score = 0

    years_non_cut = snapshot.years_non_cut_dividend or 0
    if years_non_cut >= 10:
        score += 12
    elif years_non_cut >= 5:
        score += 8
    elif years_non_cut >= 3:
        score += 5
    elif years_non_cut >= 1:
        score += 2

    years_non_decrease = snapshot.years_non_decrease_dividend or 0
    if years_non_decrease >= 10:
        score += 8
    elif years_non_decrease >= 5:
        score += 6
    elif years_non_decrease >= 3:
        score += 4
    elif years_non_decrease >= 1:
        score += 2

    if snapshot.progressive_dividend_flag:
        score += 5

    cut_count = snapshot.dividend_cut_count_10y if snapshot.dividend_cut_count_10y is not None else 99
    if cut_count == 0:
        score += 5
    elif cut_count == 1:
        score += 2

    return min(score, 30)


def compute_financial_soundness_score(snapshot: TickerSnapshot) -> int:
    score = 0

    if snapshot.is_financial:
        roe = snapshot.roe or 0.0
        if roe >= 0.12:
            score += 7
        elif roe >= 0.08:
            score += 5
        elif roe >= 0.05:
            score += 3

        if snapshot.shareholder_return_policy_flag:
            score += 4

        if snapshot.buyback_recent_2y or snapshot.doe_policy_flag:
            score += 4

        return min(score, 15)

    equity_ratio = snapshot.equity_ratio or 0.0
    if equity_ratio >= 0.50:
        score += 8
    elif equity_ratio >= 0.40:
        score += 6
    elif equity_ratio >= 0.30:
        score += 4
    elif equity_ratio >= 0.20:
        score += 2

    roe = snapshot.roe or 0.0
    if roe >= 0.12:
        score += 7
    elif roe >= 0.08:
        score += 4
    elif roe >= 0.05:
        score += 2

    return min(score, 15)


def compute_cashflow_soundness_score(snapshot: TickerSnapshot) -> int:
    if snapshot.is_financial:
        return 0

    score = 0

    years_positive_ocf = snapshot.years_positive_operating_cf or 0
    if years_positive_ocf >= 6:
        score += 9
    elif years_positive_ocf >= 4:
        score += 7
    elif years_positive_ocf >= 2:
        score += 4

    years_positive_fcf = snapshot.years_positive_fcf or 0
    if years_positive_fcf >= 6:
        score += 8
    elif years_positive_fcf >= 4:
        score += 6
    elif years_positive_fcf >= 2:
        score += 3

    if snapshot.fcf is not None and snapshot.fcf > 0:
        score += 3

    if (
        snapshot.operating_cf is not None
        and snapshot.net_income is not None
        and snapshot.net_income > 0
    ):
        gap_ratio = abs(snapshot.operating_cf - snapshot.net_income) / abs(snapshot.net_income)
        if snapshot.operating_cf >= snapshot.net_income or gap_ratio < 0.30:
            score += 3

    return min(score, 20)


def compute_earnings_stability_score(snapshot: TickerSnapshot) -> int:
    eps_score = score_series(snapshot.eps_5y, high_score=6, medium_score=3)
    operating_profit_score = score_series(snapshot.operating_profit_5y, high_score=5, medium_score=3)
    revenue_score = score_series(snapshot.revenue_5y, high_score=4, medium_score=2)

    total = eps_score + operating_profit_score + revenue_score
    return min(total, 15)


def compute_shareholder_policy_score(snapshot: TickerSnapshot) -> int:
    score = 0

    if snapshot.progressive_dividend_flag:
        score += 4
    if snapshot.doe_policy_flag:
        score += 3
    if snapshot.buyback_recent_2y:
        score += 2
    if snapshot.shareholder_return_policy_flag:
        score += 1

    return min(score, 10)


def compute_yield_overheat_score(snapshot: TickerSnapshot) -> int:
    score = 0

    if snapshot.dividend_yield is not None and snapshot.dividend_yield >= 0.035:
        score += 2

    if (
        snapshot.dividend_yield is not None
        and snapshot.yield_avg_5y is not None
        and snapshot.yield_avg_5y > 0
    ):
        overheat_ratio = (snapshot.yield_avg_5y - snapshot.dividend_yield) / snapshot.yield_avg_5y
        if overheat_ratio > 0.30:
            score -= 3

    if (not snapshot.is_financial) and snapshot.dividend_yield is not None and snapshot.dividend_yield < 0.03:
        score -= 3

    return max(-3, min(score, 5))


def compute_sector_adjustment_score(snapshot: TickerSnapshot) -> int:
    tags = set(snapshot.sector_tags)
    score = 0

    if "core_stable" in tags:
        score += 1
    if "trading_house" in tags:
        score += 1
    if "cyclical" in tags:
        score -= 1
    if "small_cap" in tags:
        score -= 2

    return max(-2, min(score, 5))


def evaluate_scoring(snapshot: TickerSnapshot) -> ScoreResult:
    score_dividend_stability = compute_dividend_stability_score(snapshot)
    score_financial_soundness = compute_financial_soundness_score(snapshot)
    score_cashflow_soundness = compute_cashflow_soundness_score(snapshot)
    score_earnings_stability = compute_earnings_stability_score(snapshot)
    score_shareholder_policy = compute_shareholder_policy_score(snapshot)
    score_yield_overheat = compute_yield_overheat_score(snapshot)
    score_sector_adjustment = compute_sector_adjustment_score(snapshot)

    total_score = (
        score_dividend_stability
        + score_financial_soundness
        + score_cashflow_soundness
        + score_earnings_stability
        + score_shareholder_policy
        + score_yield_overheat
        + score_sector_adjustment
    )

    return ScoreResult(
        score_dividend_stability=score_dividend_stability,
        score_financial_soundness=score_financial_soundness,
        score_cashflow_soundness=score_cashflow_soundness,
        score_earnings_stability=score_earnings_stability,
        score_shareholder_policy=score_shareholder_policy,
        score_yield_overheat=score_yield_overheat,
        score_sector_adjustment=score_sector_adjustment,
        total_score=total_score,
    )