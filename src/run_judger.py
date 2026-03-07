from __future__ import annotations

from datetime import date
from pathlib import Path
import csv

from schema import build_ticker_snapshots
from quality import evaluate_data_quality
from filters import evaluate_filters
from scoring import evaluate_scoring
from actions import decide_action


TODAY = date.today()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def judge_one(snapshot) -> dict:
    data_quality = evaluate_data_quality(snapshot=snapshot, today=TODAY)
    filters = evaluate_filters(snapshot=snapshot, data_quality_status=data_quality.status)

    if data_quality.status in {"SKIPPED", "INVALID"}:
        return {
            "ticker": snapshot.ticker,
            "company_name": snapshot.company_name,
            "investment_grade": "SKIPPED",
            "data_quality_status": data_quality.status,
            "caution_score": 0,
            "total_score": 0,
            "action": "SKIPPED",
            "exclude_reasons": "|".join(data_quality.reasons),
            "caution_reasons": "",
            "action_reason": "data_quality_block",
            "is_held": int(snapshot.is_held),
            "shares": snapshot.shares,
            "current_position_weight": snapshot.current_position_weight,
            "sector_weight_now": snapshot.sector_weight_now,
            "nisa_flag": int(snapshot.nisa_flag),
            "score_dividend_stability": 0,
            "score_financial_soundness": 0,
            "score_cashflow_soundness": 0,
            "score_earnings_stability": 0,
            "score_shareholder_policy": 0,
            "score_yield_overheat": 0,
            "score_sector_adjustment": 0,
        }

    scores = evaluate_scoring(snapshot)
    action_result = decide_action(
        snapshot=snapshot,
        data_quality=data_quality,
        filters=filters,
        scores=scores,
    )

    return {
        "ticker": snapshot.ticker,
        "company_name": snapshot.company_name,
        "investment_grade": action_result.investment_grade,
        "data_quality_status": data_quality.status,
        "caution_score": filters.caution_score,
        "total_score": scores.total_score,
        "action": action_result.action,
        "exclude_reasons": "|".join(filters.exclude_reasons),
        "caution_reasons": "|".join(data_quality.reasons + filters.caution_reasons),
        "action_reason": action_result.action_reason,
        "is_held": int(snapshot.is_held),
        "shares": snapshot.shares,
        "current_position_weight": snapshot.current_position_weight,
        "sector_weight_now": snapshot.sector_weight_now,
        "nisa_flag": int(snapshot.nisa_flag),
        "score_dividend_stability": scores.score_dividend_stability,
        "score_financial_soundness": scores.score_financial_soundness,
        "score_cashflow_soundness": scores.score_cashflow_soundness,
        "score_earnings_stability": scores.score_earnings_stability,
        "score_shareholder_policy": scores.score_shareholder_policy,
        "score_yield_overheat": scores.score_yield_overheat,
        "score_sector_adjustment": scores.score_sector_adjustment,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict]) -> None:
    lines: list[str] = []
    lines.append("# judged_watchlist")
    lines.append("")
    lines.append(f"- generated_at: {TODAY.isoformat()}")
    lines.append(f"- total_tickers: {len(rows)}")
    lines.append("")

    lines.append("| ticker | company_name | held | grade | dq | caution | score | action |")
    lines.append("|---|---|---:|---|---|---:|---:|---|")

    for row in rows:
        lines.append(
            f"| {row['ticker']} | {row['company_name']} | {row['is_held']} | "
            f"{row['investment_grade']} | {row['data_quality_status']} | "
            f"{row['caution_score']} | {row['total_score']} | {row['action']} |"
        )

    lines.append("")
    lines.append("## details")
    lines.append("")

    for row in rows:
        lines.append(f"### {row['ticker']} {row['company_name']}")
        lines.append(f"- action: {row['action']}")
        lines.append(f"- action_reason: {row['action_reason']}")
        lines.append(f"- investment_grade: {row['investment_grade']}")
        lines.append(f"- data_quality_status: {row['data_quality_status']}")
        lines.append(f"- caution_score: {row['caution_score']}")
        lines.append(f"- total_score: {row['total_score']}")
        lines.append(f"- is_held: {row['is_held']}")
        lines.append(f"- shares: {row['shares']}")
        lines.append(f"- current_position_weight: {row['current_position_weight']}")
        lines.append(f"- sector_weight_now: {row['sector_weight_now']}")
        lines.append(f"- nisa_flag: {row['nisa_flag']}")
        lines.append(f"- exclude_reasons: {row['exclude_reasons']}")
        lines.append(f"- caution_reasons: {row['caution_reasons']}")
        lines.append(
            f"- score_breakdown: dividend={row['score_dividend_stability']}, "
            f"financial={row['score_financial_soundness']}, "
            f"cashflow={row['score_cashflow_soundness']}, "
            f"earnings={row['score_earnings_stability']}, "
            f"policy={row['score_shareholder_policy']}, "
            f"yield_overheat={row['score_yield_overheat']}, "
            f"sector_adj={row['score_sector_adjustment']}"
        )
        lines.append("")

    with path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    ensure_output_dir()

    snapshots = build_ticker_snapshots(
        master_path=str(DATA_DIR / "master_watchlist.csv"),
        fundamentals_path=str(DATA_DIR / "fundamentals_snapshot.csv"),
        events_path=str(DATA_DIR / "events_snapshot.csv"),
        portfolio_path=str(DATA_DIR / "portfolio_snapshot.csv"),
    )

    judged = [judge_one(snapshot) for snapshot in snapshots]

    judged.sort(
        key=lambda x: (
            x["action"] != "BUY",
            x["action"] != "ADD",
            x["action"] != "HOLD",
            -x["total_score"],
            x["ticker"],
        )
    )

    csv_path = OUTPUT_DIR / "judged_watchlist.csv"
    md_path = OUTPUT_DIR / "judged_watchlist.md"

    write_csv(csv_path, judged)
    write_markdown(md_path, judged)

    print(f"Judged {len(judged)} tickers.")
    print("Outputs:")
    print(f"- {csv_path}")
    print(f"- {md_path}")


if __name__ == "__main__":
    main()