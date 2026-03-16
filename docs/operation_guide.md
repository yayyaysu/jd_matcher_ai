# JD Matcher v2 操作說明

這份文件是給第一次接手這個系統的人看的。

目標只有三件事：
- 一眼看懂這個系統在做什麼
- 知道怎麼啟動
- 知道平常要去哪裡操作、去哪裡看結果

## 這個系統是做什麼的

JD Matcher v2 是一個「職缺整理與履歷策略工具」。

它會把貼進來的 Job Description 先存起來，再用 OpenAI 做兩件事：

1. Parser
   把單一職缺分析成結構化資料，例如公司、職稱、cluster、fit score、關鍵字、gap、建議履歷版本。

2. Strategist
   把同一類職缺的分析結果聚合起來，產出對應的履歷修改策略與 markdown 檔案。

## 一眼看懂系統架構

使用者操作的入口只有 2 個：
- Streamlit UI
- CLI

後端實際流程：

1. 使用者新增 JD
2. FastAPI 接收請求
3. MySQL 保存 job、analysis、workflow、strategy
4. Redis 快取 parser / strategist 結果
5. OpenAI 產生分析與策略
6. 匯出 markdown / csv 到 `data/outputs/`

可以把它想成這樣：

`UI / CLI -> FastAPI -> Redis + MySQL + OpenAI -> outputs`

## 主要功能

### 1. 新增職缺
- 貼上 JD 內容
- 存進 `jobs`
- 建立初始 `workflow`

### 2. 分析職缺
- 讀取 `resume.txt`
- 產生 `job_analysis`
- 更新 `workflow.priority` 與 `next_action`

### 3. 查看近期職缺
- 看每筆 job 的公司、職稱、cluster、fit score、priority、status
- 可手動重跑分析
- 可標記已投遞

### 4. 生成履歷策略
- 依 cluster / company / min score 聚合分析結果
- 產生履歷策略 markdown
- 保存到 `resume_strategy`

### 5. 匯出結果
- `jobs.csv`
- `dash.md`
- `resume_versions.md`
- `strategy_*.md`

## 啟動前要準備什麼

至少需要：
- Docker Desktop
- OpenAI API Key

另外這兩個檔案也要有：
- `.env`
- `resume.txt`

如果 `.env` 還沒建立：

```powershell
copy .env.example .env
```

然後把 `.env` 裡的 `OPENAI_API_KEY` 填上。

## 最簡單啟動方式

在專案根目錄執行：

```powershell
docker compose up --build
```

第一次啟動時，MySQL 會先初始化，所以 API 可能要等幾秒到幾十秒。

## 啟動成功後看哪裡

- API Docs: `http://localhost:8000/docs`
- Streamlit UI: `http://localhost:8501`
- phpMyAdmin: `http://localhost:8080`

正常情況下，Docker 應該會有這幾個服務：
- `jd_matcher_v2_api`
- `jd_matcher_v2_frontend`
- `jd_matcher_v2_mysql`
- `jd_matcher_v2_redis`
- `jd_matcher_v2_phpmyadmin`

## 最簡單使用流程

### 用 UI 操作

打開 `http://localhost:8501` 後，主要看 3 個分頁。

#### Add Job
- 貼上 JD
- 可填 company / role title / url
- 按 `Add Job`
- 如果勾選 `Analyze immediately after adding`，會立即跑 parser

#### Recent Jobs
- 看最近 jobs
- 看分析結果有沒有出來
- 看 priority / status / next action
- 可以手動 `Re-analyze`
- 可以 `Mark Applied`

#### Strategy
- 選 cluster
- 可設定 company filter 與 min score
- 按 `Generate Strategy`
- 會產生 markdown 策略內容

### 用 CLI 操作

常用指令：

```powershell
python -m app add-jd --file .\sample_jd.txt --auto-analyze
python -m app list-jobs --cluster A --min-score 70
python -m app run-parser
python -m app run-strategist --cluster A --min-score 75
python -m app export
```

適合情境：
- 想批次跑分析
- 想直接匯出結果
- 不想開 UI

## 資料會存到哪裡

### MySQL 資料表
- `jobs`: 原始 JD 與基本資訊
- `job_analysis`: parser 分析結果
- `workflow`: 投遞與優先級狀態
- `resume_strategy`: strategist 結果

### Redis
- parser cache
- strategy cache

### 輸出檔案
都在 `data/outputs/`：
- `jobs.csv`
- `dash.md`
- `resume_versions.md`
- `strategy_*.md`
- `strategy_INDEX*.md`
- `token_usage.txt`

## 日常操作建議

每天最常見的流程：

1. 在 `Add Job` 新增新的 JD
2. 到 `Recent Jobs` 檢查 fit score、priority、status
3. 到 `Strategy` 針對高分 cluster 產策略
4. 需要整理輸出時，執行 `python -m app export`
5. 到 `data/outputs/` 看產出的 markdown 與 csv

## 出問題先看哪裡

### API 起不來
- 先看 `docker compose logs api`
- 再看 `docker compose logs mysql`

### MySQL 還沒準備好
- 第一次啟動很常見
- 通常等初始化完成即可

### OpenAI 沒有回應
- 確認 `.env` 的 `OPENAI_API_KEY` 是否正確
- 確認 API container 有讀到 `.env`

### 看不到輸出檔
- 檢查 `data/outputs/`
- 檢查 strategist 或 export 是否真的執行成功

## 推薦閱讀順序

如果你是第一次接手，建議照這個順序看：

1. 先看這份文件
2. 再看根目錄的 [README.md](../README.md)
3. 要看技術拆分，再看 [architecture.md](architecture.md)

## 一句話總結

這個系統就是：

把職缺收進來，用 AI 分析成結構化資料，再把同類職缺整理成可直接用來改履歷的策略。