# 舊版架構分析（Phase 1）

## 舊版系統在做什麼
- 透過 CLI 或 Streamlit 輸入 JD（文字或網址）。
- 使用 OpenAI 解析 JD（分群、關鍵字、缺口、分數）。
- 以 SQLite 儲存職缺、分析結果與 workflow 狀態。
- 依群組產生履歷策略 markdown，並輸出 CSV/報表。

## 主要模組責任
- `app.py`：Streamlit UI + 流程編排 + DB 讀寫 + OpenAI 呼叫。
- `jd_matcher/cli.py`：CLI 命令入口（init/migrate/add/analyze/export/strategy/delete）。
- `jd_matcher/db.py`：SQLite schema、migration、CRUD、資料一致性檢查。
- `jd_matcher/workflows.py`：分析與策略的整段流程。
- `jd_matcher/services/*`：OpenAI client、parser、strategist、exporter。
- `jd_matcher/config.py`：環境設定、resume 讀取、hash。

## SQLite 使用位置
- 預設資料庫：`data/jobs.db`。
- 主要表：`jobs`、`job_analysis`、`workflow`、`resume_strategy`。
- 存取方式：`sqlite3` 直接查詢，分散在 UI/CLI/workflows。

## OpenAI 使用位置
- `jd_matcher/services/openai_client.py`：Responses API 封裝、重試、JSON 解析。
- `jd_matcher/services/parser.py`：JD 分析。
- `jd_matcher/services/strategist.py`：履歷策略生成。
- 由 `app.py` 與 `jd_matcher/cli.py` 觸發。

## 混層問題（UI 與後端責任耦合）
- `app.py` 同時負責 UI、流程控制、資料存取、模型調用。
- CLI 也有一套相似流程，造成重複實作。
- 結果是 API 邊界不清楚，後續服務化改造成本高。

## v2 建議保留的概念
- JD 結構化分析輸出（keywords / score / cluster / gaps）。
- 重複計算快取思路。
- 分析歷史保存。
- 與舊資料脫鉤的遷移腳本策略。

## v2 必須重設計的部分
- 建立 FastAPI 為主的 API 邊界。
- 分離 router / schema / service / db / cache。
- 從 sqlite3 直連改為 SQLAlchemy + MySQL。
- 用 Redis 管理快取 key（`jd_analysis:{sha256(jd_text)}`）。
- 舊系統只讀不改，由獨立腳本遷移資料。
