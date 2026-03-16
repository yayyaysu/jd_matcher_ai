# JD Matcher v2 架構說明

## 設計原則（面試版）
1. 先有清楚邊界，再談功能擴充
2. 每一層只做一件事
3. 只保留能展示能力的最小實作

## 一句話架構
`Streamlit UI` -> `FastAPI Router` -> `JDAnalysisService` -> `Redis / MatchService / MySQL`

## 分層責任
1. Router：`app/api/routers`
   - 定義 endpoint 與參數
   - 保持薄，避免塞商業邏輯
2. Schema：`app/schemas`
   - Pydantic 驗證請求
   - 固定回應結構，降低前後端契約漂移
3. Service：`app/services/jd_analysis_service.py`
   - 編排流程：cache miss 才分析，分析後寫入 DB
   - 將分析細節委派給 `app/services/match_service.py`
   - 不包含 UI、HTTP 或資料庫 schema 細節
4. Cache：`app/services/cache_service.py`
   - key：`jd_analysis:{sha256(jd_text)}`
   - 目標：避免重複輸入重複計算
5. DB：`app/db`
   - SQLAlchemy model + session
   - `analysis_records` 保存歷史結果，供查詢/追蹤
   - app 啟動會先等待 MySQL ready 再建表
6. Frontend：`ui/app.py`
   - 只有輸入與顯示，不帶分析邏輯

## 核心執行流程（POST /analysis/jd）
1. Router 收到 `jd_text`，交給 service。
2. Service 以 `sha256(jd_text)` 組 cache key 查 Redis。
3. 命中快取：直接回傳，不重跑分析。
4. 未命中：
   - `match_service` 先正規化文字，再抽取技術關鍵字
   - 用 cluster skill map 比對 matched / missing skills
   - 選出分數最高的推薦職類與 score
   - 寫入 MySQL `analysis_records`
   - 回寫 Redis（TTL 可設定）
5. 回傳標準化 Pydantic response。

## 我在這個版本刻意不做的事
1. 不導入過多抽象（repository、factory、plugin 架構）
2. 不提早加入背景任務系統（Celery/queue）
3. 不做完整 auth 與 RBAC

## 為什麼這樣更像後端作品集
1. 能快速看到 FastAPI/Pydantic/Redis/MySQL 的整合點
2. 可以直接啟動、測試、Demo
3. 保留遷移腳本，展現對 legacy 系統治理能力

## 3 分鐘面試講解腳本
1. 先交代重構動機：舊版 UI/流程/資料存取混層，難以維護。
2. 再講層次：router 只收 request，service 編排流程，schema 管契約。
3. 點出 async 與 Redis：同樣 JD 輸入直接 cache hit，降低重算成本。
4. 點出 MySQL：分析結果留痕，`/history` 可展示資料連續性。
5. 最後補 migration：用獨立腳本從 SQLite 搬資料，不耦合舊程式碼。
