# data_schema.md

このドキュメントは、`jp_high_dividend_auto_judger` が使用する入力データの列仕様を定義します。  
目的は、CSV / Google Sheets / 自動取得パイプラインのどれからでも、同じ入力スキーマへ正規化できるようにすることです。

---

## 基本方針

- 1銘柄 = 1行を基本とする
- 市場データと財務データは鮮度を別管理する
- 欠損時は原則として強引に補完しない
- `SKIPPED` は正式な出力状態である
- 金融と非金融は一部必須列が異なる

---

## 入力ファイル

- `data/master_watchlist.csv`
- `data/fundamentals_snapshot.csv`
- `data/events_snapshot.csv`

---

# 1. master_watchlist.csv

監視銘柄マスタ。  
比較的変化しにくい情報を保持する。

## 列一覧

| 列名 | 型 | 必須 | 内容 |
|---|---:|---:|---|
| ticker | string | yes | 銘柄コード |
| company_name | string | yes | 会社名 |
| exchange | string | yes | 取引所。通常は TSE |
| sector_33 | string | yes | 東証33業種 |
| sector_large | string | yes | システム用大分類 |
| sector_detail | string | yes | システム用詳細分類 |
| sector_tags | string | yes | `|` 区切りの複数タグ |
| is_financial | int/bool | yes | 金融判定 |
| is_core_candidate | int/bool | yes | 主力候補になりうるか |
| is_active | int/bool | yes | 監視対象として有効か |

## `sector_tags` の例

- `financial`
- `core_stable`
- `telecom`
- `trading_house`
- `infrastructure`
- `cyclical`
- `small_cap`

複数ある場合は `|` 区切りで保持する。  
例: `trading_house|commodity_sensitive`

---

# 2. fundamentals_snapshot.csv

判定の中核となるスナップショット。  
原則として 1銘柄1行。

## 共通必須列

| 列名 | 型 | 必須 | 内容 |
|---|---:|---:|---|
| ticker | string | yes | 銘柄コード |
| asof_market | date(YYYY-MM-DD) | yes | 市場データ基準日 |
| asof_financial | date(YYYY-MM-DD) | yes | 財務データ基準日 |
| market_cap_jpy | float | yes | 時価総額 |
| avg_daily_value_20d_jpy | float | yes | 20営業日平均売買代金 |
| dividend_yield | float | yes | 現在配当利回り。3.5% は `0.035` |
| annual_dividend_per_share | float | yes | 今期年間配当予想 |
| annual_dividend_per_share_prev | float | yes | 前期年間配当実績 or 直前値 |
| payout_ratio | float | yes | 配当性向 |
| roe | float | yes | ROE |
| years_non_cut_dividend | int | yes | 連続非減配年数 |
| years_non_decrease_dividend | int | yes | 連続増配 or 維持年数 |
| dividend_cut_count_10y | int | yes | 過去10年の減配回数 |
| progressive_dividend_flag | int/bool | yes | 累進配当方針 |
| doe_policy_flag | int/bool | yes | DOE方針 |
| buyback_recent_2y | int/bool | yes | 直近2年の自己株買い |
| shareholder_return_policy_flag | int/bool | yes | 明文化された株主還元方針あり |
| yield_avg_5y | float | yes | 過去5年平均利回り |

## 非金融で追加必須

| 列名 | 型 | 必須 | 内容 |
|---|---:|---:|---|
| equity_ratio | float | yes | 自己資本比率 |
| operating_cf | float | yes | 営業CF |
| fcf | float | yes | FCF |
| net_income | float | yes | 純利益 |
| operating_profit | float | yes | 営業利益 |
| ordinary_profit | float | yes | 経常利益 |
| years_positive_operating_cf | int | yes | 営業CFプラス継続年数 |
| years_positive_fcf | int | yes | FCFプラス継続年数 |
| eps_5y | string | yes | `|` 区切り5年分 EPS |
| operating_profit_5y | string | yes | `|` 区切り5年分 営業利益 |
| revenue_5y | string | yes | `|` 区切り5年分 売上高 |

## 金融で省略可

以下は金融では省略可。

- equity_ratio
- operating_cf
- fcf
- years_positive_operating_cf
- years_positive_fcf
- operating_profit
- ordinary_profit

---

## 5年履歴データの保存形式

CSVでは配列を直接持てないため、`|` 区切り文字列で保持する。

例:

- `eps_5y = "120|128|135|149|162"`
- `operating_profit_5y = "1650|1680|1700|1740|1780"`
- `revenue_5y = "12100000|12300000|12500000|12700000|12900000"`

Python側で読み込み時に `list[float]` へ変換する。

---

# 3. events_snapshot.csv

直近開示タイトルや市場反応を保持する。

## 列一覧

| 列名 | 型 | 必須 | 内容 |
|---|---:|---:|---|
| ticker | string | yes | 銘柄コード |
| recent_disclosure_titles | string | no | `|` 区切り直近開示タイトル |
| gap_down_ratio | float | no | 決算後ギャップダウン率 |
| abnormal_volume_down_flag | int/bool | no | 異常出来高を伴う下落 |
| has_exclude_keyword | int/bool | no | EXCLUDE語あり |
| has_caution_keyword | int/bool | no | CAUTION語あり |
| has_positive_keyword | int/bool | no | POSITIVE語あり |

---

# 4. データ品質ルール

## 品質ステータス

- `OK`
- `STALE`
- `MISSING`
- `INVALID`
- `SKIPPED`

## 判定基準

### 市場データ鮮度
- `asof_market` が 5営業日以内 → `OK`
- それを超える → `STALE_MARKET`

### 財務データ鮮度
- `asof_financial` が 365日以内 → `OK`
- 366〜550日 → `STALE_FINANCIAL`
- 551日以上 → `INVALID_FINANCIAL`

### 欠損
新規買いに必要な必須列が欠けている場合は `SKIPPED`。

---

# 5. 欠損時の扱い

## 原則
- 欠損を強引に補完しない
- 前期値流用は原則しない
- データ欠損だけで EXIT しない

## アクション制御
- `BUY`: `OK` のみ許可
- `ADD`: 軽度 stale market は許容、stale financial は不可
- `HOLD`: データ問題があっても原則維持候補に回せる
- `EXIT`: EXCLUDE 条件が別途成立している場合のみ

---

# 6. 金融分岐

`is_financial = 1` の場合、以下を原則スキップする。

- equity_ratio ベース評価
- operating_cf ベース評価
- fcf ベース評価
- net debt / EBITDA 的な評価

金融は主に以下で判定する。

- payout_ratio
- roe
- years_non_cut_dividend
- progressive_dividend_flag
- doe_policy_flag
- buyback_recent_2y
- shareholder_return_policy_flag

---

# 7. 出力に必要な列

最終出力 `judged_watchlist.csv` は最低限以下を含む。

| 列名 | 内容 |
|---|---|
| ticker | 銘柄コード |
| company_name | 会社名 |
| investment_grade | PASS / FAIL / SKIPPED |
| data_quality_status | OK / STALE / MISSING / INVALID |
| caution_score | caution合計 |
| total_score | 総合スコア |
| action | BUY / ADD / HOLD / TRIM / EXIT / WATCH / SKIPPED |
| exclude_reasons | `|` 区切り理由 |
| caution_reasons | `|` 区切り理由 |
| score_breakdown | スコア内訳 |
| sector_weight_after_trade | 売買後のセクター比率 |
| position_weight_after_trade | 売買後の銘柄比率 |

---

# 8. 備考

このスキーマは CSV / Google Sheets / 自動取得パイプラインの共通入力を想定している。  
将来的に API やスクレイピングへ移行しても、このスキーマへの正規化を守ることで判定ロジックを変更せずに再利用できる。