from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional
import csv


def parse_date(value: str) -> Optional[date]:
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_bool(value) -> bool:
    if value is None:
        return False
    s = str(value).strip().lower()
    return s in {"1", "true", "yes", "y", "t"}


def parse_float(value) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    return float(s)


def parse_int(value) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    return int(float(s))


def parse_pipe_floats(value: str) -> List[float]:
    if value is None:
        return []
    s = str(value).strip()
    if s == "":
        return []
    return [float(x) for x in s.split("|") if str(x).strip() != ""]


def parse_pipe_strings(value: str) -> List[str]:
    if value is None:
        return []
    s = str(value).strip()
    if s == "":
        return []
    return [x.strip() for x in s.split("|") if x.strip()]


@dataclass
class WatchlistMaster:
    ticker: str
    company_name: str
    exchange: str
    sector_33: str
    sector_large: str
    sector_detail: str
    sector_tags: List[str]
    is_financial: bool
    is_core_candidate: bool
    is_active: bool


@dataclass
class FundamentalsSnapshot:
    ticker: str
    asof_market: Optional[date]
    asof_financial: Optional[date]

    market_cap_jpy: Optional[float]
    avg_daily_value_20d_jpy: Optional[float]
    dividend_yield: Optional[float]

    annual_dividend_per_share: Optional[float]
    annual_dividend_per_share_prev: Optional[float]
    payout_ratio: Optional[float]
    roe: Optional[float]
    equity_ratio: Optional[float]

    operating_cf: Optional[float]
    fcf: Optional[float]
    net_income: Optional[float]
    operating_profit: Optional[float]
    ordinary_profit: Optional[float]

    years_non_cut_dividend: Optional[int]
    years_non_decrease_dividend: Optional[int]
    dividend_cut_count_10y: Optional[int]
    years_positive_operating_cf: Optional[int]
    years_positive_fcf: Optional[int]

    eps_5y: List[float] = field(default_factory=list)
    operating_profit_5y: List[float] = field(default_factory=list)
    revenue_5y: List[float] = field(default_factory=list)

    progressive_dividend_flag: bool = False
    doe_policy_flag: bool = False
    buyback_recent_2y: bool = False
    shareholder_return_policy_flag: bool = False

    yield_avg_5y: Optional[float] = None


@dataclass
class EventsSnapshot:
    ticker: str
    recent_disclosure_titles: List[str]
    gap_down_ratio: Optional[float]
    abnormal_volume_down_flag: bool
    has_exclude_keyword: bool
    has_caution_keyword: bool
    has_positive_keyword: bool


@dataclass
class TickerSnapshot:
    ticker: str
    company_name: str
    exchange: str
    sector_33: str
    sector_large: str
    sector_detail: str
    sector_tags: List[str]
    is_financial: bool
    is_core_candidate: bool
    is_active: bool

    asof_market: Optional[date]
    asof_financial: Optional[date]

    market_cap_jpy: Optional[float]
    avg_daily_value_20d_jpy: Optional[float]
    dividend_yield: Optional[float]

    annual_dividend_per_share: Optional[float]
    annual_dividend_per_share_prev: Optional[float]
    payout_ratio: Optional[float]
    roe: Optional[float]
    equity_ratio: Optional[float]

    operating_cf: Optional[float]
    fcf: Optional[float]
    net_income: Optional[float]
    operating_profit: Optional[float]
    ordinary_profit: Optional[float]

    years_non_cut_dividend: Optional[int]
    years_non_decrease_dividend: Optional[int]
    dividend_cut_count_10y: Optional[int]
    years_positive_operating_cf: Optional[int]
    years_positive_fcf: Optional[int]

    eps_5y: List[float]
    operating_profit_5y: List[float]
    revenue_5y: List[float]

    progressive_dividend_flag: bool
    doe_policy_flag: bool
    buyback_recent_2y: bool
    shareholder_return_policy_flag: bool

    yield_avg_5y: Optional[float]

    recent_disclosure_titles: List[str]
    gap_down_ratio: Optional[float]
    abnormal_volume_down_flag: bool
    has_exclude_keyword: bool
    has_caution_keyword: bool
    has_positive_keyword: bool

    def has_required_common_fields(self) -> bool:
        required = [
            self.ticker,
            self.company_name,
            self.asof_market,
            self.asof_financial,
            self.market_cap_jpy,
            self.avg_daily_value_20d_jpy,
            self.dividend_yield,
            self.annual_dividend_per_share,
            self.annual_dividend_per_share_prev,
            self.payout_ratio,
            self.roe,
            self.years_non_cut_dividend,
            self.years_non_decrease_dividend,
            self.dividend_cut_count_10y,
            self.yield_avg_5y,
        ]
        return all(x is not None and x != "" for x in required)

    def has_required_non_financial_fields(self) -> bool:
        if self.is_financial:
            return True
        required = [
            self.equity_ratio,
            self.operating_cf,
            self.fcf,
            self.net_income,
            self.operating_profit,
            self.ordinary_profit,
            self.years_positive_operating_cf,
            self.years_positive_fcf,
        ]
        return all(x is not None and x != "" for x in required)

    def has_minimum_history(self) -> bool:
        if self.is_financial:
            return len(self.eps_5y) >= 5
        return (
            len(self.eps_5y) >= 5
            and len(self.operating_profit_5y) >= 5
            and len(self.revenue_5y) >= 5
        )


def load_master_watchlist(path: str) -> dict[str, WatchlistMaster]:
    items: dict[str, WatchlistMaster] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = WatchlistMaster(
                ticker=row["ticker"].strip(),
                company_name=row["company_name"].strip(),
                exchange=row["exchange"].strip(),
                sector_33=row["sector_33"].strip(),
                sector_large=row["sector_large"].strip(),
                sector_detail=row["sector_detail"].strip(),
                sector_tags=parse_pipe_strings(row["sector_tags"]),
                is_financial=parse_bool(row["is_financial"]),
                is_core_candidate=parse_bool(row["is_core_candidate"]),
                is_active=parse_bool(row["is_active"]),
            )
            items[item.ticker] = item
    return items


def load_fundamentals_snapshot(path: str) -> dict[str, FundamentalsSnapshot]:
    items: dict[str, FundamentalsSnapshot] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = FundamentalsSnapshot(
                ticker=row["ticker"].strip(),
                asof_market=parse_date(row["asof_market"]),
                asof_financial=parse_date(row["asof_financial"]),
                market_cap_jpy=parse_float(row["market_cap_jpy"]),
                avg_daily_value_20d_jpy=parse_float(row["avg_daily_value_20d_jpy"]),
                dividend_yield=parse_float(row["dividend_yield"]),
                annual_dividend_per_share=parse_float(row["annual_dividend_per_share"]),
                annual_dividend_per_share_prev=parse_float(row["annual_dividend_per_share_prev"]),
                payout_ratio=parse_float(row["payout_ratio"]),
                roe=parse_float(row["roe"]),
                equity_ratio=parse_float(row["equity_ratio"]),
                operating_cf=parse_float(row["operating_cf"]),
                fcf=parse_float(row["fcf"]),
                net_income=parse_float(row["net_income"]),
                operating_profit=parse_float(row["operating_profit"]),
                ordinary_profit=parse_float(row["ordinary_profit"]),
                years_non_cut_dividend=parse_int(row["years_non_cut_dividend"]),
                years_non_decrease_dividend=parse_int(row["years_non_decrease_dividend"]),
                dividend_cut_count_10y=parse_int(row["dividend_cut_count_10y"]),
                years_positive_operating_cf=parse_int(row["years_positive_operating_cf"]),
                years_positive_fcf=parse_int(row["years_positive_fcf"]),
                eps_5y=parse_pipe_floats(row["eps_5y"]),
                operating_profit_5y=parse_pipe_floats(row["operating_profit_5y"]),
                revenue_5y=parse_pipe_floats(row["revenue_5y"]),
                progressive_dividend_flag=parse_bool(row["progressive_dividend_flag"]),
                doe_policy_flag=parse_bool(row["doe_policy_flag"]),
                buyback_recent_2y=parse_bool(row["buyback_recent_2y"]),
                shareholder_return_policy_flag=parse_bool(row["shareholder_return_policy_flag"]),
                yield_avg_5y=parse_float(row["yield_avg_5y"]),
            )
            items[item.ticker] = item
    return items


def load_events_snapshot(path: str) -> dict[str, EventsSnapshot]:
    items: dict[str, EventsSnapshot] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = EventsSnapshot(
                ticker=row["ticker"].strip(),
                recent_disclosure_titles=parse_pipe_strings(row["recent_disclosure_titles"]),
                gap_down_ratio=parse_float(row["gap_down_ratio"]),
                abnormal_volume_down_flag=parse_bool(row["abnormal_volume_down_flag"]),
                has_exclude_keyword=parse_bool(row["has_exclude_keyword"]),
                has_caution_keyword=parse_bool(row["has_caution_keyword"]),
                has_positive_keyword=parse_bool(row["has_positive_keyword"]),
            )
            items[item.ticker] = item
    return items


def build_ticker_snapshots(
    master_path: str,
    fundamentals_path: str,
    events_path: str,
) -> List[TickerSnapshot]:
    masters = load_master_watchlist(master_path)
    funds = load_fundamentals_snapshot(fundamentals_path)
    events = load_events_snapshot(events_path)

    snapshots: List[TickerSnapshot] = []

    for ticker, m in masters.items():
        f = funds.get(ticker)
        e = events.get(ticker)

        snapshot = TickerSnapshot(
            ticker=m.ticker,
            company_name=m.company_name,
            exchange=m.exchange,
            sector_33=m.sector_33,
            sector_large=m.sector_large,
            sector_detail=m.sector_detail,
            sector_tags=m.sector_tags,
            is_financial=m.is_financial,
            is_core_candidate=m.is_core_candidate,
            is_active=m.is_active,

            asof_market=f.asof_market if f else None,
            asof_financial=f.asof_financial if f else None,

            market_cap_jpy=f.market_cap_jpy if f else None,
            avg_daily_value_20d_jpy=f.avg_daily_value_20d_jpy if f else None,
            dividend_yield=f.dividend_yield if f else None,

            annual_dividend_per_share=f.annual_dividend_per_share if f else None,
            annual_dividend_per_share_prev=f.annual_dividend_per_share_prev if f else None,
            payout_ratio=f.payout_ratio if f else None,
            roe=f.roe if f else None,
            equity_ratio=f.equity_ratio if f else None,

            operating_cf=f.operating_cf if f else None,
            fcf=f.fcf if f else None,
            net_income=f.net_income if f else None,
            operating_profit=f.operating_profit if f else None,
            ordinary_profit=f.ordinary_profit if f else None,

            years_non_cut_dividend=f.years_non_cut_dividend if f else None,
            years_non_decrease_dividend=f.years_non_decrease_dividend if f else None,
            dividend_cut_count_10y=f.dividend_cut_count_10y if f else None,
            years_positive_operating_cf=f.years_positive_operating_cf if f else None,
            years_positive_fcf=f.years_positive_fcf if f else None,

            eps_5y=f.eps_5y if f else [],
            operating_profit_5y=f.operating_profit_5y if f else [],
            revenue_5y=f.revenue_5y if f else [],

            progressive_dividend_flag=f.progressive_dividend_flag if f else False,
            doe_policy_flag=f.doe_policy_flag if f else False,
            buyback_recent_2y=f.buyback_recent_2y if f else False,
            shareholder_return_policy_flag=f.shareholder_return_policy_flag if f else False,

            yield_avg_5y=f.yield_avg_5y if f else None,

            recent_disclosure_titles=e.recent_disclosure_titles if e else [],
            gap_down_ratio=e.gap_down_ratio if e else None,
            abnormal_volume_down_flag=e.abnormal_volume_down_flag if e else False,
            has_exclude_keyword=e.has_exclude_keyword if e else False,
            has_caution_keyword=e.has_caution_keyword if e else False,
            has_positive_keyword=e.has_positive_keyword if e else False,
        )
        snapshots.append(snapshot)

    return snapshots