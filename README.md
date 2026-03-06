# jp_high_dividend_auto_judger

日本株高配当株の監視・判定を、**安定性重視**で半自動化するためのプロトタイプです。  
最終的な発注は人間が行いますが、それ以前の

- 監視銘柄の足切り
- 投資適格判定
- caution判定
- スコアリング
- BUY / ADD / HOLD / TRIM / EXIT 判定

までは自動で行うことを目的とします。

---

## 基本思想

このシステムは、単純な高利回り追求ではなく、以下を重視します。

- 減配しにくさ
- 配当方針の明確さ
- 財務健全性
- キャッシュフロー健全性
- 業績の安定性
- 説明可能な判定ロジック

### 重要な前提

- 手動の定性フラグは使わない
- 公開情報・数値・イベントのみで判定する
- データ欠損・鮮度不足時は強引に判定しない
- 見逃しより事故回避を優先する
- 最終発注のみ人間が行う

---

## 判定の流れ

1. データ品質チェック
2. hard filter
3. caution scoring
4. stability-first scoring
5. portfolio constraints
6. action decision

### 出力アクション

- BUY
- ADD
- HOLD
- TRIM
- EXIT
- WATCH
- SKIPPED

---

## ディレクトリ構成

```text
.
├─ README.md
├─ config/
│  └─ rules.yaml
├─ data/
│  ├─ master_watchlist.csv
│  ├─ fundamentals_snapshot.csv
│  └─ events_snapshot.csv
├─ docs/
│  └─ data_schema.md
├─ output/
│  ├─ judged_watchlist.csv
│  └─ judged_watchlist.md
└─ src/
   ├─ schema.py
   ├─ quality.py
   ├─ filters.py
   ├─ scoring.py
   ├─ actions.py
   └─ run_judger.py

---

## セットアップ

### 1. 仮想環境を作成
```bash
make setup