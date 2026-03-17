# JD Matcher v2

JD Matcher v2 是一個把「職缺整理、AI 分析、投遞追蹤、履歷策略產生」整合在一起的求職系統。

它的核心目標不是單純做 JD 分析，而是把零散的職缺資訊整理成可行動的決策流程：
- 先收集職缺
- 再分析履歷與職缺的匹配程度
- 接著追蹤是否已投遞
- 最後根據同類型職缺，產出履歷修改策略

## 專案概覽

- **產品價值**：把原本靠人工整理的求職流程，變成可追蹤、可重複、可輸出的系統。
- **技術重點**：FastAPI 後端、service layer 分層、MySQL 持久化、Redis 快取 AI 回應、Streamlit 操作介面。
- **主要使用者**：求職者、想展示完整 AI 應用架構的工程師、需要快速理解系統價值的面試官。

## 系統架構

整體資料流如下：

`Streamlit UI / CLI -> FastAPI Router -> Service Layer -> MySQL / Redis / OpenAI -> UI 與輸出檔案`

系統中的主要模組：
- **FastAPI routers**：接收請求、驗證參數、呼叫 service
- **Service layer**：處理 job、parser、strategy、export 等商業邏輯
- **MySQL**：保存 jobs、job_analysis、workflow、resume_strategy
- **Redis**：只用來快取 parser 與 strategist 的 AI 回應
- **OpenAI**：負責結構化 parser 與 strategy 生成
- **Streamlit**：提供 Add Job、Recent Jobs、Strategy 三個操作頁面

## 主要功能

- 從 UI 或 CLI 新增職缺
- 用 OpenAI 將 JD 轉成結構化分析結果
- 根據分析結果更新 priority 與 application workflow
- 依公司、cluster、分數、applied status 篩選工作
- 針對某一群職缺產生履歷策略 markdown
- 匯出 `jobs.csv`、`dash.md`、`resume_versions.md` 等檔案

## 技術棧

- Python
- FastAPI
- SQLAlchemy
- MySQL
- Redis
- OpenAI Responses API
- Streamlit
- Docker Compose

## 範例流程

1. 在 UI 新增一筆 job description。
2. 系統執行 parser，產生 cluster、fit score、gap、履歷調整建議。
3. 在 Recent Jobs 檢查高分職缺，並標記哪些已投遞。
4. 在 Strategy 頁面針對特定 cluster 生成履歷策略。
5. 到 `data/outputs/` 取得 markdown 與 csv 輸出。

## CI（GitHub Actions）+ Local CD（Docker hub）

本專案的交付流程是：開發者 `git push` 後，由 GitHub Actions 自動 build backend / frontend images 並 push 到 Docker Hub；本機或展示環境再透過 Docker Compose 啟動或更新容器。

```powershell
copy .env.example .env
docker compose up --build
```

更新最新 image：

```powershell
.\update.ps1
```

必要條件：
- `.env` 內要設定 `OPENAI_API_KEY`

主要網址：
- API Docs: `http://localhost:8000/docs`
- Streamlit UI: `http://localhost:8501`
- phpMyAdmin: `http://localhost:8080`

## 文件

- 系統使用與啟動說明：[docs/operation_guide.md](docs/operation_guide.md)
- 開發者 / AI agent 設計文件：[docs/system_design.md](docs/system_design.md)

## 這個專案的技術亮點

- 有清楚的分層邊界：router、service、cache、db、UI 各自負責不同事情
- 使用結構化 AI 輸出，不是單純文字 prompt 回答
- Redis 只做快取，不混入持久化責任
- 同時具備 UI、API、資料庫、快取、AI 整合與輸出檔案流程，適合做完整作品展示

## 畫面說明

目前 repo 沒有附截圖，但 Streamlit UI 已提供三個主要頁面：
- Add Job
- Recent Jobs
- Strategy
