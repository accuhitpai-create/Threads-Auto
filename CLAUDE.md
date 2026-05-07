# Threads AI 自動發文系統

每天自動生成 2 篇 AI 與數位轉型相關貼文，透過 Notion 審稿後自動發布到 Threads。

## 系統架構

```
07:00  generate.py  → 依內容比例選支柱，呼叫 Gemini 生成，建立到 Notion（待審核）
                              ↓ 人工在 Notion 審稿
10:00  publish.py   → 取「核准發布」文章，發布主文 → 留言1 → 留言2
19:30  publish.py   → 同上（晚上那篇）
```

GitHub Actions 負責排程，台灣時間（UTC+8）。

## 帳號定位

**AI 與數據大師**（銷售 AI 數據解決方案）

口吻：專業、清晰、直接破題，像朋友在分享，不武斷不行銷腔。

## 內容策略

**6 大支柱：** 生產力提升 / 數位工具應用 / 會員經營 / AI提示詞 / 數位轉型 / 自動化行銷

**內容類型比例（60/25/10/5）：**
| 類型 | 比例 | 支柱 |
|------|------|------|
| 純知識 | 60% | 全部支柱 |
| 工具評測 | 25% | 生產力提升、數位工具應用 |
| 軟性露出 | 10% | 會員經營、自動化行銷 |
| 硬推廣 | 5% | 綜合 |

## 檔案職責

| 檔案 | 職責 |
|------|------|
| `generate.py` | 每天生成邏輯；`CONTENT_TYPE_WEIGHTS` 調整比例，`PILLAR_BY_TYPE` 調整支柱 |
| `publish.py` | 從 Notion 撈「核准發布」的文章並發布 |
| `claude_service.py` | 呼叫 Google Gemini API（名稱雖叫 claude，實際用 Gemini） |
| `notion_service.py` | Notion 資料庫的 CRUD 操作 |
| `threads_service.py` | Threads Graph API 的發布邏輯 |
| `prompts.py` | 所有 Prompt 模板；`SYSTEM_PROMPT` 控制全局口吻 |
| `config.py` | 金鑰讀取、Gemini 模型、Notion 欄位名稱、`CONSULTATION_LINK` |

## 必改設定（接手時）

**1. `config.py` — 諮詢連結**
```python
CONSULTATION_LINK = "https://your-domain.com/contact"  # 換成自己的
```

**2. `.env` — 5 個金鑰**（複製 `.env.example` 填入）
```
NOTION_TOKEN=
NOTION_DATABASE_ID=
GOOGLE_API_KEY=
THREADS_USER_ID=
THREADS_ACCESS_TOKEN=
```

**3. GitHub Actions Secrets** — 同 `.env` 的 5 個欄位名稱，讓排程能跑

## Notion 資料庫欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| 標題 | Title | AI 自動生成 |
| 支柱 | Select | 6 大支柱 |
| 內容類型 | Select | 純知識 / 工具評測 / 軟性露出 / 硬推廣 |
| 預定發布日 | Date | 台灣時間日期 |
| 發布時間 | Select | `10:00` 或 `19:30` |
| 主文 | Text | 150–250 字 |
| 留言1 | Text | 延伸內容或 Prompt 範本 |
| 留言2 | Text | 軟性 CTA + 諮詢連結 |
| 審稿狀態 | Select | 待審核 → 核准發布 → 已發布（或需修改） |
| 備註 | Text | 填修改意見，隔天自動重生成 |

## 調整 Prompt 或口吻

- **全局口吻**：`prompts.py` 的 `SYSTEM_PROMPT`
- **各支柱自動生成模板**：`AUTO_PILLAR_TEMPLATES`（`generate.py` 呼叫）
- **修改模式模板**：`PILLAR_TEMPLATES`（審稿備註觸發時使用）

Threads 不支援 Markdown，強調只用換行、引號、emoji，條列用 `●` 或數字。

## 維護提醒

- **Threads Access Token 每 60 天過期**，需手動更新 `.env` 和 GitHub Secrets
- 執行 log 在 GitHub Actions 頁面查看，或本機 `logs/` 目錄
- 手動測試：GitHub → Actions → 選 workflow → Run workflow
