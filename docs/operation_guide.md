# 操作與使用說明

這份文件是給「第一次接手這個專案的人」看的。

目標不是講架構細節，而是讓初階工程師也能快速知道：
- 這個系統在做什麼
- 專案怎麼啟動
- 重要檔案放哪裡
- 平常怎麼操作
- 問題出現時先看哪裡

## 這個系統在做什麼

JD Matcher v2 是一個求職輔助系統。

它會把 job description 收進來，再用 OpenAI 做兩件事：

1. **Parser**
	 把單一職缺分析成結構化資料，例如：
	 - Company
	 - Role Title
	 - Cluster
	 - Fit Score
	 - 關鍵字
	 - Gap
	 - 建議履歷版本

2. **Strategist**
	 把同一類職缺的分析結果聚合，產出履歷策略 markdown。

簡單來說，這個系統把「看職缺 -> 判斷要不要投 -> 改履歷」這條流程系統化。

## 系統入口

你平常最常接觸的是這三個入口：

- Streamlit UI
- FastAPI API
- phpMyAdmin

## Main URLs

系統啟動後，主要網址如下：

- Streamlit UI: `http://localhost:8501`
- FastAPI Docs: `http://localhost:8000/docs`
- FastAPI Health: `http://localhost:8000/health`
- phpMyAdmin: `http://localhost:8080`

## 啟動專案

### 1. 先準備 `.env`

如果還沒有 `.env`，先執行：

```powershell
copy .env.example .env
```

至少要確認 `.env` 內有：

- `OPENAI_API_KEY`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_ROOT_PASSWORD`
- `REDIS_URL`

通常最重要的是 `OPENAI_API_KEY`。

### 2. 啟動專案

在專案根目錄執行：

```powershell
docker compose up --build
```

如果要背景執行：

```powershell
docker compose up --build -d
```

### 3. 確認服務是否起來

正常情況下應該會有：

- `jd_matcher_v2_api`
- `jd_matcher_v2_frontend`
- `jd_matcher_v2_mysql`
- `jd_matcher_v2_redis`
- `jd_matcher_v2_phpmyadmin`

第一次啟動時 MySQL 初始化需要時間，所以 API 可能會先等一下才起來，這是正常現象。

## 重要檔案放哪裡

### Resume 放哪裡

系統會讀取 `RESUME_PATH` 指向的檔案。

預設設定是：

- `RESUME_PATH=data/resume.txt`

系統會依序嘗試找：

1. `jd_matcher_v2/resume.txt`
2. `jd-matcher/resume.txt`
3. container 內的 `/legacy/jd-matcher/resume.txt`

如果你想明確指定履歷位置，可以直接在 `.env` 設定：

```env
RESUME_PATH=data/resume.txt
```

最簡單做法：
- 如果你要讓 v2 自己管理履歷，就把 `resume.txt` 放在 `jd_matcher_v2` 根目錄

### Prompt 放哪裡

Prompt 檔案放在：

- `app/prompts/parser_prompt.txt`
- `app/prompts/strategist_prompt.txt`

Schema 檔案放在：

- `app/prompts/schemas.py`

如果你要調整 parser 或 strategist 的 AI 行為，通常改的是這裡。

### 輸出檔案放哪裡

輸出檔案在：

- `data/outputs/`

常見檔案：
- `jobs.csv`
- `dash.md`
- `resume_versions.md`
- `strategy_*.md`
- `strategy_INDEX*.md`
- `token_usage.txt`

### UI 放哪裡

Streamlit UI 相關檔案在：

- `ui/app.py`
- `ui/pages/add_job.py`
- `ui/pages/recent_jobs.py`
- `ui/pages/strategy.py`

### 後端主要程式放哪裡

- routers: `app/api/routers/`
- services: `app/services/`
- models: `app/db/models/`
- config: `app/core/config.py`

## 平常怎麼使用系統

### 1. 新增職缺

打開 Streamlit UI 的 `Add Job` 頁面：

1. 貼上 JD
2. 視需要填 company / role title / url
3. 按 `Add Job`
4. 如果勾選立即分析，系統會馬上跑 parser

### 2. 查看與篩選職缺

打開 `Recent Jobs` 頁面：

你可以看到：
- Company
- Role Title
- Cluster
- Fit Score
- Priority
- Applied
- Created Date

可用篩選：
- Company
- Cluster
- Minimum Fit Score
- Applied Status

### 3. 重新分析職缺

在 `Recent Jobs` 每筆 job 下方都有：

- `Run Parser`

點下去會重新執行 parser。

### 4. 標記已投遞

在 `Recent Jobs` 內可直接按：

- `Mark Applied`
- `Mark Not Applied`

### 5. 刪除職缺

在 `Recent Jobs` 內可按：

- `Delete Job`

系統會再要求一次確認，確認後會刪除：
- job 本身
- 對應 analysis
- workflow

### 6. 生成履歷策略

打開 `Strategy` 頁面：

1. 選擇 Cluster
2. 視需要選擇 Company
3. 設定 Minimum Score
4. 按 `Generate Strategy`

畫面會直接顯示 markdown 結果。

## CLI 怎麼用

除了 UI，也可以直接用 CLI：

```powershell
python -m app add-jd --file .\sample_jd.txt --auto-analyze
python -m app list-jobs --cluster A --min-score 70
python -m app run-parser
python -m app run-strategist --cluster A --min-score 75
python -m app export
```

適合情境：
- 想批次操作
- 想快速匯出
- 不想開瀏覽器 UI

## 快速驗證系統有沒有正常

### 檢查健康狀態

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/health"
```

### 新增一筆 job

```powershell
$body = @{
	jd_text = "We need a backend engineer with Python, FastAPI, MySQL, Redis and Docker experience."
	auto_analyze = $true
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/jobs/add" -ContentType "application/json" -Body $body
```

### 查詢 jobs

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/jobs?limit=5"
```

### 生成 strategy

```powershell
$strategy = @{
	cluster = "A"
	filter_min_score = 70
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/strategy/generate" -ContentType "application/json" -Body $strategy
```

## 資料與狀態存在哪裡

### MySQL

主要表：
- `jobs`
- `job_analysis`
- `workflow`
- `resume_strategy`
- `analysis_records`

### Redis

Redis 只負責快取 AI 結果，不是主資料來源。

### phpMyAdmin

如果你要直接看資料庫內容：

- 網址：`http://localhost:8080`
- Server: `mysql`
- Username: `root`
- Password: `.env` 裡的 `MYSQL_ROOT_PASSWORD`

## 常見問題

### 1. API 起不來

先看：

```powershell
docker compose logs api
docker compose logs mysql
```

### 2. MySQL is not ready after retries

通常代表：
- MySQL 還在初始化
- 連線資訊錯
- image 需要重 build

先試：

```powershell
docker compose down
docker compose up --build
```

### 3. OpenAI 沒有回應

先檢查：
- `.env` 的 `OPENAI_API_KEY` 是否正確
- API container 是否真的讀到 `.env`

### 4. UI 看不到資料

先確認：
- API 有起來
- `/jobs` endpoint 可正常回應
- 篩選條件是否太嚴格

如果畫面顯示：

`No jobs match current filters.`

表示目前篩選條件下沒有資料，不一定是系統壞掉。

### 5. 找不到輸出檔案

先看：
- `data/outputs/`

如果沒有新檔案，通常代表 strategist 或 export 沒有真的成功執行。

## 建議閱讀順序

如果你是新加入的工程師，建議這樣看：

1. 先看這份 `operation_guide.md`
2. 再看根目錄 `README.md`
3. 最後看 `docs/system_design.md`

## 一句話總結

這個系統就是：

把職缺收進來，用 AI 分析成結構化資料，再把同類職缺整理成可執行的履歷策略與投遞流程。