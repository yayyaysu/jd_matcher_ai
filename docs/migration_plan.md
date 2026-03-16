# SQLite -> MySQL 遷移計畫（Phase 1）

## 舊版資料來源
- 來源資料庫：`../jd-matcher/data/jobs.db`（可透過參數覆寫）。
- 主要可用表：
  - `jobs`
  - `job_analysis`
  - `workflow`
  - `resume_strategy`

## 新版目標表
- 目標：MySQL `analysis_records`。
- 欄位：
  - `id`
  - `jd_text`
  - `matched_keywords`
  - `missing_keywords`
  - `score`（float）
  - `cluster`
  - `created_at`

## 欄位映射策略（best-effort）
- 主要來源：`job_analysis` 左連 `jobs`。
- 對應方式：
  - `jd_text` <- `jobs.jd_text`
  - `missing_keywords` <- `top_gaps`
  - `matched_keywords` <- `must_have_keywords + domain_keywords - top_gaps`
  - `score` <- `fit_score`
  - `cluster` <- `cluster`
  - `created_at` <- `job_analysis.created_at`（無值時 fallback `jobs.created_at`）

## 降級策略
- 若 `job_analysis` 不存在，退化為只搬 `jobs`：
  - keyword 欄位為空陣列
  - `score = 0.0`
  - `cluster = C2`

## 限制與假設
- 舊表中的 JSON 字串若格式錯誤，視為空陣列。
- `matched_keywords` 為推導值，舊版沒有直接欄位。
- Phase 1 不搬 `workflow` 與 `resume_strategy`，避免範圍膨脹。
- 目前採 append-only；去重策略可在後續版本加入。

## 使用方式
```bash
python scripts/migrate_sqlite_to_mysql.py --sqlite-path ../jd-matcher/data/jobs.db
```

預設會優先讀取 `DATABASE_URL`，若未設定則使用 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE` 組成連線字串。
