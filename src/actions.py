from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from schema import TickerSnapshot
from quality import DataQualityResult, can_new_buy, can_add_position, hold_with_data_issue
from filters import FilterResult
from scoring import ScoreResult


@dataclass
class ActionResult:
    investment_grade: str
    action: str
    action_reason: str


def get_effective_max_position_weight(snapshot: TickerSnapshot, default_max: float = 0.10) -> float:
    if snapshot.max_position_weight_override is not None:
        return snapshot.max_position_weight_override
    return default_max


def is_over_position_limit(snapshot: TickerSnapshot, default_max: float = 0.10) -> bool:
    if snapshot.current_position_weight is None:
        return False
    return snapshot.current_position_weight > get_effective_max_position_weight(snapshot, default_max)


def is_over_sector_limit(snapshot: TickerSnapshot, default_limit: float = 0.25) -> bool:
    if snapshot.sector_weight_now is None:
        return False

    if snapshot.is_financial:
        return snapshot.sector_weight_now > 0.25

    tags = set(snapshot.sector_tags)

    if "cyclical" in tags:
        return snapshot.sector_weight_now > 0.15
    if "small_cap" in tags:
        return snapshot.sector_weight_now > 0.10
    if "infrastructure" in tags:
        return snapshot.sector_weight_now > 0.20
    if "telecom" in tags:
        return snapshot.sector_weight_now > 0.25
    if "trading_house" in tags:
        return snapshot.sector_weight_now > 0.25

    return snapshot.sector_weight_now > default_limit


def should_force_exit(snapshot: TickerSnapshot, data_quality: DataQualityResult, filters: FilterResult) -> bool:
    if data_quality.status == "INVALID":
        return True

    if filters.exclude_reasons:
        return True

    if filters.caution_score >= 4:
        return True

    return False


def should_watch_only(data_quality: DataQualityResult, filters: FilterResult) -> bool:
    if data_quality.status == "STALE":
        return True

    if filters.caution_score >= 3:
        return True

    return False


def choose_non_held_action(
    snapshot: TickerSnapshot,
    data_quality: DataQualityResult,
    filters: FilterResult,
    scores: ScoreResult,
) -> ActionResult:
    if data_quality.status in {"SKIPPED", "INVALID"}:
        return ActionResult(
            investment_grade="SKIPPED",
            action="SKIPPED",
            action_reason="data_quality_block",
        )

    if should_force_exit(snapshot, data_quality, filters):
        return ActionResult(
            investment_grade="FAIL",
            action="EXIT",
            action_reason="exclude_or_caution_triggered",
        )

    if should_watch_only(data_quality, filters):
        return ActionResult(
            investment_grade="PASS",
            action="WATCH",
            action_reason="stale_or_high_caution",
        )

    if not can_new_buy(data_quality):
        return ActionResult(
            investment_grade="PASS",
            action="WATCH",
            action_reason="new_buy_not_allowed_by_data_quality",
        )

    if is_over_sector_limit(snapshot):
        return ActionResult(
            investment_grade="PASS",
            action="WATCH",
            action_reason="sector_limit_block",
        )

    if scores.total_score >= 75:
        return ActionResult(
            investment_grade="PASS",
            action="BUY",
            action_reason="strong_score_non_held",
        )

    if scores.total_score >= 55:
        return ActionResult(
            investment_grade="PASS",
            action="WATCH",
            action_reason="monitor_candidate_non_held",
        )

    return ActionResult(
        investment_grade="PASS",
        action="WATCH",
        action_reason="low_score_non_held",
    )


def choose_held_action(
    snapshot: TickerSnapshot,
    data_quality: DataQualityResult,
    filters: FilterResult,
    scores: ScoreResult,
) -> ActionResult:
    if should_force_exit(snapshot, data_quality, filters):
        if snapshot.nisa_flag:
            return ActionResult(
                investment_grade="FAIL",
                action="WATCH",
                action_reason="nisa_held_force_exit_softened_to_watch",
            )
        return ActionResult(
            investment_grade="FAIL",
            action="EXIT",
            action_reason="held_exclude_or_caution_triggered",
        )

    if is_over_position_limit(snapshot):
        return ActionResult(
            investment_grade="PASS",
            action="TRIM",
            action_reason="position_limit_exceeded",
        )

    if is_over_sector_limit(snapshot):
        return ActionResult(
            investment_grade="PASS",
            action="TRIM",
            action_reason="sector_limit_exceeded",
        )

    if should_watch_only(data_quality, filters):
        if hold_with_data_issue(data_quality):
            return ActionResult(
                investment_grade="PASS",
                action="HOLD",
                action_reason="held_with_data_issue_or_high_caution",
            )
        return ActionResult(
            investment_grade="PASS",
            action="WATCH",
            action_reason="held_watch_due_to_risk",
        )

    if scores.total_score >= 70 and can_add_position(data_quality):
        return ActionResult(
            investment_grade="PASS",
            action="ADD",
            action_reason="strong_score_held",
        )

    if scores.total_score >= 55:
        return ActionResult(
            investment_grade="PASS",
            action="HOLD",
            action_reason="mid_score_held",
        )

    return ActionResult(
        investment_grade="PASS",
        action="WATCH",
        action_reason="weak_score_held",
    )


def decide_action(
    snapshot: TickerSnapshot,
    data_quality: DataQualityResult,
    filters: FilterResult,
    scores: ScoreResult,
) -> ActionResult:
    if snapshot.is_held:
        return choose_held_action(snapshot, data_quality, filters, scores)
    return choose_non_held_action(snapshot, data_quality, filters, scores)