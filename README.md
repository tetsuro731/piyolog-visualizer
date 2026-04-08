# piyolog-visualizer

PiyoLog（ぴよログ）のエクスポートデータを前処理・分析・可視化するパイプライン。

## フロー概要

```
raw_data/*.txt
      │
      ▼  preprocess.py
processed_data/piyolog.csv
      │
      ├──▶ notebook/analysis.ipynb  （Python による EDA）
      │
      └──▶ tableau/piyo.twb         （Tableau による可視化）
```

---

## 1. 生データの準備

PiyoLog アプリからエクスポートした `.txt` ファイルを月ごとに `raw_data/` に配置する。

```
raw_data/
  2023_11_Nov.txt
  2023_12_Dec.txt
  2024_01_Jan.txt
  ...
```

ファイルの区切りは `----------`、各行は `HH:MM イベント名 ...` の形式。

---

## 2. 前処理（raw → CSV）

`preprocess.py` を実行すると `raw_data/*.txt` をすべて読み込み、`processed_data/piyolog.csv` を生成する。

```bash
uv run preprocess
```

または直接実行する場合:

```bash
uv run python preprocess.py
```

### 主な加工内容

| 処理 | 内容 |
|------|------|
| 日付の匿名化 | 実際の誕生日を `2023-01-01` 起算にシフト（プライバシー保護） |
| `days_from_birth` | 誕生日からの経過日数を付与 |
| イベント正規化 | `Formula` → `formula` のように snake_case に統一 |
| ミルク量抽出 | `Formula 100ml` → `milk_amount = 100` |
| 睡眠時間抽出 | `Wake-up (2h 40m)` → `sleep_minutes = 160` |
| スキップ | `Body Temp` など分析対象外のイベントを除外 |

### 出力カラム

| カラム | 型 | 説明 |
|--------|----|------|
| `date` | str | 匿名化後の日付（YYYY-MM-DD） |
| `datetime` | str | 匿名化後の日時 |
| `days_from_birth` | int | 誕生日からの経過日数 |
| `time` | str | 時刻（HH:MM） |
| `event` | str | イベント種別 |
| `milk_amount` | int/null | ミルク量（ml）、formula のみ |
| `sleep_minutes` | int/null | 睡眠時間（分）、wake_up のみ |

---

## 3. Jupyter Notebook での分析


`notebook/analysis.ipynb`を実行する。

### 分析内容

- **Daily Milk Intake** — 日ごとのミルク総量の推移
- **Sleep Duration** — 日ごとの睡眠時間合計の推移
- **Monthly Averages** — 月齢ごとの1回あたり平均ミルク量
- **Event Frequency by Hour** — 時間帯別のイベント頻度分布

---

## 4. Tableau での可視化

`tableau/piyo.twb`のような形式で Tableau Desktop を開く想定。データソースは `processed_data/piyolog.csv` を参照する。
今回はtwb fileはpushしていないが、成果物は以下のURLから見ることができる。

https://public.tableau.com/app/profile/tetsuro.sugiura/viz/piyo/Dashboard1


---

## セットアップ

```bash
# 依存ライブラリのインストール
uv sync

# 前処理実行
uv run preprocess
```

依存パッケージ: `polars`, `matplotlib`, `numpy`, `jupyter`（`pyproject.toml` 参照）
- uv + pyproject.tomlでの環境構築を前提

for day_block in days:
    lines = day_block.strip().split("\n")
    if not lines:
        continue

    # Find date line (format: "Sat, Jul 1, 2024")
    current_date = None
    for line in lines:
        parsed_date = parse_date(line)
        if parsed_date:
            current_date = parsed_date
            break

    if not current_date:
        continue

    # Calculate day number from birth
    days_from_birth = (current_date - birth_date).days
    if days_from_birth < 0:
        continue

    dummy_date = DUMMY_BIRTH_DATE + timedelta(days=days_from_birth)

    # Parse event lines
    for line in lines:
        event = parse_event_line(line)
        if event:
            event["date"] = dummy_date.strftime("%Y-%m-%d")
            event["datetime"] = f"{dummy_date.strftime('%Y-%m-%d')} {event['time']}"
            event["days_from_birth"] = days_from_birth
            event["time"] = event.pop("time")
            events.append(event)