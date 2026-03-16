# JD Matcher v2

把舊版 Streamlit + SQLite + OpenAI 混層工具，拆成可以獨立展示的後端系統：FastAPI 負責 API，Redis 負責 parser / strategist 快取，MySQL 保存 jobs / analysis / workflow / strategy，Streamlit 只保留薄前端。

## 快速入口

- 想快速看懂系統怎麼用：`docs/operation_guide.md`
- 想看完整技術與 API 說明：這份 README

## Legacy 到新架構
- 舊版：`jd-matcher/app.py` 同時處理 UI、JD 輸入、SQLite、OpenAI 分析、策略生成、檔案輸出。
- 新版：`router -> service -> cache/db`，UI 改成只呼叫 API，不再內嵌分析邏輯。
- 保留 legacy prompt、schema、parser、strategist、export 核心邏輯，但移植到既有 FastAPI / Redis / MySQL 架構。

## 現在的實際流程
1. 使用者在 Streamlit UI 的 `Add Job` 分頁貼上 JD，或用 CLI `python -m app add-jd` 匯入。
2. API `POST /jobs/add` 建立 `jobs` 與初始 `workflow`。
3. `POST /jobs/analyze` 讀取 `resume.txt`，用 Redis key `parser:{job_id}:{analysis_version}:{resume_hash}` 查 parser 快取。
4. 未命中時由 OpenAI parser 依 legacy `parser_prompt.txt` + `PARSER_SCHEMA` 產生 `job_analysis`。
5. parser 根據 `fit_score / years_required / top_gaps` 更新 `workflow.priority` 與 `next_action`。
6. `POST /strategy/generate` 依 cluster / company / min_score 聚合 `job_analysis`，用 Redis 與 `resume_strategy` 快取策略結果。
7. strategist 產生 markdown，寫入 `data/outputs/strategy_*.md`，同時更新 `resume_strategy` 與 `strategy_INDEX*.md`。
8. `export` 會把 `jobs.csv`、`dash.md`、`resume_versions.md` 輸出到 `data/outputs/`。

## 主要 API
- `POST /jobs/add`：新增 JD，可選 `auto_analyze=true`。
- `POST /jobs/analyze`：分析單筆或全部 jobs，寫入 `job_analysis` 與 `workflow`。
- `GET /jobs`：查看近期 jobs，可用 `cluster / status / priority / company / min_score / applied` 過濾。
- `PATCH /jobs/{job_id}/workflow`：更新 application status、priority、notes、next action。
- `DELETE /jobs/{job_id}`：刪除單筆 job 與其當前 analysis/workflow。
- `POST /strategy/generate`：為單一 cluster 或全部 cluster 生成策略 markdown。
- `GET /strategy`：查詢已生成的策略。
- `POST /analysis/jd` / `GET /history`：保留既有簡化版分析能力，方便回歸測試。

## 專案結構
- `app/api/routers`：薄路由，只做 request/response 與依賴注入
- `app/services/parser_service.py`：Bot1 parser 分析、workflow priority 更新
- `app/services/strategy_service.py`：Bot2 strategist 聚合、快取、markdown 產生
- `app/services/export_service.py`：輸出 `jobs.csv`、`dash.md`、`resume_versions.md`
- `app/services/openai_client.py`：OpenAI Responses API + retry + token log
- `app/prompts`：legacy prompt 與 schema
- `app/db`：SQLAlchemy model / session
- `app/cache`：Redis client
- `ui/app.py`：Add Job / Recent Jobs / Strategy 三分頁前端
- `scripts/create_mysql_tables.py`：建立 MySQL tables
- `scripts/migrate_sqlite_to_mysql.py`：從舊 SQLite 搬既有紀錄

## 執行方式
```powershell
copy .env.example .env
docker compose up --build
```

必填環境變數：
- `OPENAI_API_KEY`

可選環境變數：
- `PARSER_MODEL`
- `STRATEGIST_MODEL`
- `RESUME_PATH`
- `OUTPUTS_DIR`

啟動後：
- API Docs: `http://localhost:8000/docs`
- Streamlit UI: `http://localhost:8501`
- phpMyAdmin: `http://localhost:8080`

CLI：
```powershell
python -m app add-jd --file .\sample_jd.txt --auto-analyze
python -m app list-jobs --cluster A --min-score 70
python -m app run-parser
python -m app run-strategist --cluster A --min-score 75
python -m app export
```

## 實際啟動流程
第一次啟動時，MySQL 需要先初始化資料目錄、建立 `jd_matcher` database 與 `jd_user` 使用者，這時 API 會先等待資料庫可連線。

建議用這個順序：

```powershell
copy .env.example .env
docker compose down
docker compose up --build
```

如果你改過依賴或 Dockerfile，要重新 build：

```powershell
docker compose down
docker compose up --build
```

如果要背景執行：

```powershell
docker compose up --build -d
docker compose ps
```

正常狀態應該看到：
- `jd_matcher_v2_mysql` 是 `healthy`
- `jd_matcher_v2_redis` 是 `healthy`
- `jd_matcher_v2_api` 是 `Up`
- `jd_matcher_v2_frontend` 是 `Up`
- `jd_matcher_v2_phpmyadmin` 是 `Up`

## 執行後如何驗證
1. 檢查健康狀態

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/health"
```

2. 實際新增並分析一筆 JD

```powershell
$body = @{
  jd_text = "We need a backend engineer with Python, FastAPI, MySQL, Redis, Docker, SQL and microservices experience."
  auto_analyze = $true
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/jobs/add" -ContentType "application/json" -Body $body
```

3. 檢查近期 jobs

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/jobs?limit=5"
```

4. 生成策略

```powershell
$strategy = @{
  cluster = "A"
  filter_min_score = 70
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/strategy/generate" -ContentType "application/json" -Body $strategy
```

5. 開啟前端 UI
- `http://localhost:8501`
- `Add Job`：新增 JD 並可立即分析
- `Recent Jobs`：查看 cluster / fit score / priority / status，支援手動 re-analyze 與 mark applied
- `Strategy`：生成或查看策略 markdown

6. 開啟 phpMyAdmin 看 MySQL 資料
- 網址：`http://localhost:8080`
- Server: `mysql`
- Username: `root`
- Password: `.env` 裡的 `MYSQL_ROOT_PASSWORD`，預設是 `root_password`
- 登入後選 `jd_matcher` database，可檢查 `jobs`、`job_analysis`、`workflow`、`resume_strategy`

## 常見問題
1. API 啟動失敗，log 顯示 `MySQL is not ready after retries`
   - 先看 `docker compose logs mysql`
   - 若同時看到 `cryptography package is required for sha256_password or caching_sha2_password auth methods`，代表 API image 需要重新 build 以安裝新依賴：

```powershell
docker compose down
docker compose up --build
```

2. 想清空舊資料重新測試

```powershell
docker compose down -v
docker compose up --build
```

這會刪掉 MySQL / Redis volumes，重新初始化資料。

## UI 說明
- `Add Job`：建立 job、可直接觸發 parser。
- `Recent Jobs`：顯示公司、職稱、cluster、fit score、priority、status、next action、applied。
- `Strategy`：依 cluster / company / min_score 生成或讀取既有策略。
- UI 只透過 HTTP 呼叫 API，不再帶任何分析邏輯。

## Redis / MySQL 設計
- Redis：
  - parser cache：`parser:{job_id}:{analysis_version}:{resume_hash}`
  - strategy cache：以 cluster / filters / cluster_input_hash 組 key
- MySQL：
  - `jobs`：JD 原文與基本資訊
  - `job_analysis`：OpenAI parser 結果
  - `workflow`：priority / status / next_action / applied
  - `resume_strategy`：策略快取與 markdown
- `data/outputs/`：markdown / csv / token log 輸出
- phpMyAdmin：提供瀏覽器介面檢查上述資料表

## 舊資料遷移
```powershell
docker compose run --rm api python scripts/create_mysql_tables.py
docker compose run --rm api python scripts/migrate_sqlite_to_mysql.py
```

說明：
- `create_mysql_tables.py` 會建立 `jobs`、`job_analysis`、`workflow`、`resume_strategy`、`analysis_records`
- `migrate_sqlite_to_mysql.py` 會自動偵測 host 的 `jd-matcher/data/*.db`，以及 container 內掛載的 `/legacy/jd-matcher/data/*.db`
- migration script 可重跑，已存在的 primary key 會自動跳過
- migration 完成後會更新 `docs/migration_validation.md`

## 作品集重點
- 從 legacy 混層工具拆出可維護的 backend boundary
- 保留 prompt / strategist / export 的核心能力，但改成標準 API + service + cache + DB
- Streamlit 只做操作層，核心邏輯全回到 FastAPI 服務內
