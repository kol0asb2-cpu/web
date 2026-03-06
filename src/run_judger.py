from __future__ import annotations

from dataclasses import asdict
from datetime import date
import csv
import math
import statistics
from typing import List, Tuple

from schema import TickerSnapshot, build_ticker_snapshots


TODAY = date.today()


def days_between(d1: date | None, d2: date | None) -> int | None:
    if d1 is None or d2 is None:
        return None
    return abs((d1 - d2).days)


def get_data_quality_status(s: TickerSnapshot) -> Tuple[str, List[str]]:
    reasons: List[str] = []

    if not s.has_required_common_fields():
        reasons.append("missing_common_fields")
        return "SKIPPED", reasons

    if not s.has_required_non_financial_fields():
        reasons.append("missing_non_financial_fields")
        return "SKIPPED", reasons

    if not s.has_minimum_history():
        reasons.append("insufficient_history")
        return "SKIPPED", reasons

    market_age = days_between(TODAY, s.asof_market)
    fin_age = days_between(TODAY, s.asof_financial)

    if fin_age is None:
        reasons.append("missing_financial_date")
        return "SKIPPED", reasons

    if fin_age > 550:
        reasons.append("invalid_financial_data")
        return "INVALID", reasons

    if market_age is not None and market_age > 5:
        reasons.append("stale_market_data")

    if fin_age > 365:
        reasons.append("stale_financial_data")

    if reasons:
        return "STALE", reasons

    return "OK", reasons


def calc_cv_and_declines(values: List[float]) -> Tuple[float, int, int]:
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


def compute_dividend_stability_score(s: TickerSnapshot) -> int:
    score = 0

    y1 = s.years_non_cut_dividend or 0
    if y1 >= 10:
        score += 12
    elif y1 >= 5:
        score += 8
    elif y1 >= 3:
        score += 5
    elif y1 >= 1:
        score += 2

    y2 = s.years_non_decrease_dividend or 0
    if y2 >= 10:
        score += 8
    elif y2 >= 5:
        score += 6
    elif y2 >= 3:
        score += 4
    elif y2 >= 1:
        score += 2

    if s.progressive_dividend_flag:
        score += 5

    cut_count = s.dividend_cut_count_10y if s.dividend_cut_count_10y is not None else 99
    if cut_count == 0:
        score += 5
    elif cut_count == 1:
        score += 2

    return min(score, 30)


def compute_financial_soundness_score(s: TickerSnapshot) -> int:
    score = 0

    if s.is_financial:
        roe = s.roe or 0.0
        if roe >= 0.12:
            score += 7
        elif roe >= 0.08:
            score += 5
        elif roe >= 0.05:
            score += 3

        if s.shareholder_return_policy_flag:
            score += 4
        if s.buyback_recent_2y or s.doe_policy_flag:
            score += 4

        return min(score, 15)

    equity_ratio = s.equity_ratio or 0.0
    if equity_ratio >= 0.50:
        score += 8
    elif equity_ratio >= 0.40:
        score += 6
    elif equity_ratio >= 0.30:
        score += 4
    elif equity_ratio >= 0.20:
        score += 2

    roe = s.roe or 0.0
    if roe >= 0.12:
        score += 7
    elif roe >= 0.08:
        score += 4
    elif roe >= 0.05:
        score += 2

    return min(score, 15)


def compute_cashflow_soundness_score(s: TickerSnapshot) -> int:
    if s.is_financial:
        return 0

    score = 0

    y_ocf = s.years_positive_operating_cf or 0
    if y_ocf >= 6:
        score += 9
    elif y_ocf >= 4:
        score += 7
    elif y_ocf >= 2:
        score += 4

    y_fcf = s.years_positive_fcf or 0
    if y_fcf >= 6:
        score += 8
    elif y_fcf >= 4:
        score += 6
    elif y_fcf >= 2:
        score += 3

    if s.fcf is not None and s.annual_dividend_per_share is not None and s.net_income is not None:
        # 初期版では厳密な配当総額ではなく簡易代理
        if s.fcf > 0:
            score += 3

    if s.operating_cf is not None and s.net_income is not None and s.net_income > 0:
        gap_ratio = abs(s.operating_cf - s.net_income) / abs(s.net_income)
        if s.operating_cf >= s.net_income or gap_ratio < 0.30:
            score += 3

    return min(score, 20)


def compute_earnings_stability_score(s: TickerSnapshot) -> int:
    eps_score = score_series(s.eps_5y, high_score=6, medium_score=3)
    op_score = score_series(s.operating_profit_5y, high_score=5, medium_score=3)
    rev_score = score_series(s.revenue_5y, high_score=4, medium_score=2)

    total = eps_score + op_score + rev_score
    return min(total, 15)


def compute_shareholder_policy_score(s: TickerSnapshot) -> int:
    score = 0
    if s.progressive_dividend_flag:
        score += 4
    if s.doe_policy_flag:
        score += 3
    if s.buyback_recent_2y:
        score += 2
    if s.shareholder_return_policy_flag:
        score += 1
    return min(score, 10)


def compute_yield_overheat_score(s: TickerSnapshot) -> int:
    score = 0

    if s.dividend_yield is not None and s.dividend_yield >= 0.035:
        score += 2

    if s.dividend_yield is not None and s.yield_avg_5y is not None and s.yield_avg_5y > 0:
        overheat_ratio = (s.yield_avg_5y - s.dividend_yield) / s.yield_avg_5y

        if overheat_ratio > 0.30:
            score -= 3

    if (not s.is_financial) and s.dividend_yield is not None and s.dividend_yield < 0.03:
        score -= 3

    return max(-3, min(score, 5))


def compute_sector_adjustment_score(s: TickerSnapshot) -> int:
    tags = set(s.sector_tags)
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


def check_exclude(s: TickerSnapshot) -> List[str]:
    reasons: List[str] = []

    if not s.is_active:
        reasons.append("inactive_watchlist")

    if s.dividend_yield is not None and s.dividend_yield < 0.035:
        reasons.append("below_min_dividend_yield")

    if s.market_cap_jpy is not None and s.market_cap_jpy < 10_000_000_000:
        reasons.append("below_min_market_cap")

    if s.avg_daily_value_20d_jpy is not None and s.avg_daily_value_20d_jpy < 50_000_000:
        reasons.append("below_min_liquidity")

    if (
        s.annual_dividend_per_share is not None
        and s.annual_dividend_per_share_prev is not None
        and s.annual_dividend_per_share < s.annual_dividend_per_share_prev
    ):
        reasons.append("recent_dividend_cut")

    if s.has_exclude_keyword:
        reasons.append("exclude_keyword_detected")

    if s.gap_down_ratio is not None and s.gap_down_ratio <= -0.15:
        reasons.append("severe_gap_down_after_earnings")

    if s.is_financial:
        if s.payout_ratio is not None and s.payout_ratio > 1.0:
            reasons.append("payout_ratio_too_high_financial")
    else:
        if s.payout_ratio is not None and s.payout_ratio > 1.0:
            reasons.append("payout_ratio_too_high")
        if s.equity_ratio is not None and s.equity_ratio < 0.20:
            reasons.append("equity_ratio_too_low")
        if s.years_positive_operating_cf is not None and s.years_positive_operating_cf <= 0:
            pass  # 初期版では即除外にしない

    return reasons


def compute_caution_score(s: TickerSnapshot, data_quality_status: str, data_quality_reasons: List[str]) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []

    def add(points: int, reason: str) -> None:
        nonlocal score
        score += points
        reasons.append(reason)

    if s.is_financial:
        if s.payout_ratio is not None and s.payout_ratio > 0.85:
            add(1, "high_payout_ratio_financial")
    else:
        if s.payout_ratio is not None and s.payout_ratio > 0.80:
            add(1, "high_payout_ratio")
        if s.roe is not None and s.roe < 0.05:
            add(1, "low_roe")
        if s.operating_cf is not None and s.net_income is not None and s.net_income > 0:
            if s.operating_cf < s.net_income:
                add(1, "ocf_below_net_income")

    if s.has_caution_keyword:
        add(2, "caution_keyword_detected")

    if s.gap_down_ratio is not None and s.gap_down_ratio <= -0.08:
        add(2, "earnings_gap_down")

    if s.abnormal_volume_down_flag:
        add(1, "abnormal_volume_down")

    if data_quality_status == "STALE":
        add(1, "stale_data")

    return score, reasons


def decide_action(
    data_quality_status: str,
    exclude_reasons: List[str],
    caution_score: int,
    total_score: int,
) -> Tuple[str, str]:
    if data_quality_status in {"SKIPPED", "INVALID"}:
        return "SKIPPED", "data_quality_block"

    if exclude_reasons:
        return "EXIT", "exclude_triggered"

    if caution_score >= 4:
        return "EXIT", "caution_score_ge_4"

    if caution_score >= 3:
        return "WATCH", "caution_score_ge_3"

    if total_score >= 75:
        return "BUY", "strong_score"

    if total_score >= 70:
        return "ADD", "good_score"

    if total_score >= 55:
        return "HOLD", "mid_score"

    return "WATCH", "low_score"


def judge_one(s: TickerSnapshot) -> dict:
    data_quality_status, data_quality_reasons = get_data_quality_status(s)

    if data_quality_status in {"SKIPPED", "INVALID"}:
        return {
            "ticker": s.ticker,
            "company_name": s.company_name,
            "investment_grade": "SKIPPED",
            "data_quality_status": data_quality_status,
            "caution_score": 0,
            "total_score": 0,
            "action": "SKIPPED",
            "exclude_reasons": "|".join(data_quality_reasons),
            "caution_reasons": "",
            "score_dividend_stability": 0,
            "score_financial_soundness": 0,
            "score_cashflow_soundness": 0,
            "score_earnings_stability": 0,
            "score_shareholder_policy": 0,
            "score_yield_overheat": 0,
            "score_sector_adjustment": 0,
        }

    exclude_reasons = check_exclude(s)
    caution_score, caution_reasons = compute_caution_score(s, data_quality_status, data_quality_reasons)

    score_dividend_stability = compute_dividend_stability_score(s)
    score_financial_soundness = compute_financial_soundness_score(s)
    score_cashflow_soundness = compute_cashflow_soundness_score(s)
    score_earnings_stability = compute_earnings_stability_score(s)
    score_shareholder_policy = compute_shareholder_policy_score(s)
    score_yield_overheat = compute_yield_overheat_score(s)
    score_sector_adjustment = compute_sector_adjustment_score(s)

    total_score = (
        score_dividend_stability
        + score_financial_soundness
        + score_cashflow_soundness
        + score_earnings_stability
        + score_shareholder_policy
        + score_yield_overheat
        + score_sector_adjustment
    )

    action, action_reason = decide_action(
        data_quality_status=data_quality_status,
        exclude_reasons=exclude_reasons,
        caution_score=caution_score,
        total_score=total_score,
    )

    investment_grade = "FAIL" if exclude_reasons or caution_score >= 4 else "PASS"

    return {
        "ticker": s.ticker,
        "company_name": s.company_name,
        "investment_grade": investment_grade,
        "data_quality_status": data_quality_status,
        "caution_score": caution_score,
        "total_score": total_score,
        "action": action,
        "exclude_reasons": "|".join(exclude_reasons),
        "caution_reasons": "|".join(data_quality_reasons + caution_reasons + [action_reason]),
        "score_dividend_stability": score_dividend_stability,
        "score_financial_soundness": score_financial_soundness,
        "score_cashflow_soundness": score_cashflow_soundness,
        "score_earnings_stability": score_earnings_stability,
        "score_shareholder_policy": score_shareholder_policy,
        "score_yield_overheat": score_yield_overheat,
        "score_sector_adjustment": score_sector_adjustment,
    }


def write_csv(path: str, rows: List[dict]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: str, rows: List[dict]) -> None:
    lines = []
    lines.append("# judged_watchlist")
    lines.append("")
    lines.append("| ticker | company_name | grade | dq | caution | score | action |")
    lines.append("|---|---|---:|---:|---:|---:|---|")
    for r in rows:
        lines.append(
            f"| {r['ticker']} | {r['company_name']} | {r['investment_grade']} | "
            f"{r['data_quality_status']} | {r['caution_score']} | {r['total_score']} | {r['action']} |"
        )
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    snapshots = build_ticker_snapshots(
        master_path="data/master_watchlist.csv",
        fundamentals_path="data/fundamentals_snapshot.csv",
        events_path="data/events_snapshot.csv",
    )

    judged = [judge_one(s) for s in snapshots]
    judged.sort(key=lambda x: (x["action"] != "BUY", -x["total_score"], x["ticker"]))

    write_csv("output/judged_watchlist.csv", judged)
    write_markdown("output/judged_watchlist.md", judged)

    print(f"Judged {len(judged)} tickers.")
    print("Outputs:")
    print("- output/judged_watchlist.csv")
    print("- output/judged_watchlist.md")


if __name__ == "__main__":
    main()