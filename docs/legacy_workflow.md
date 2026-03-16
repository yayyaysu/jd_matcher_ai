# Legacy Workflow

`jd-matcher/app.py` 的實際流程是把 UI、資料庫與分析流程綁在同一個 Streamlit 檔案裡。

User input  
↓  
使用者在 Streamlit 貼上 JD 文字，或提供網址讓系統抓取內容  
↓  
Text preprocessing  
把 URL 內容轉成純文字，補齊空白，確認 JD 不為空，再寫入 SQLite `jobs`  
↓  
Keyword extraction  
若勾選 `Analyze now` 或後續跑 strategy，會呼叫 `ensure_analysis()`，再由 `parser.py` 把 JD 與 resume 一起送進 OpenAI，要求輸出 must-have keywords、domain keywords、top gaps、cluster、fit score 等結構化欄位  
↓  
Matching / scoring  
OpenAI 回傳 cluster、fit score、top gaps、years required，舊系統再用這些欄位更新 `job_analysis` 與 `workflow`，算出 priority / next action  
↓  
Result formatting  
Streamlit 直接讀 SQLite，把 cluster、fit score、gaps、resume tweak suggestions 顯示在表格與 detail 區塊，也能再生成 strategy markdown 與 export 檔案

重點是：舊版的 domain workflow 是有效的，但 UI、OpenAI、DB 寫入、結果格式化全部混在同一層，這就是 v2 要拆開的部分。