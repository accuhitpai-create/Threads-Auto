# Threads AI 自動發文系統

自動生成 AI 與數位轉型相關貼文，每天產出兩篇內容並發布到 Threads。

---

## 系統架構

```
每天 07:00
generate.py
  → 依內容比例隨機選支柱 + 內容類型
  → Gemini AI 自動生成標題 + 主文 + 留言
  → 建立兩篇文章到 Notion（待審核）

        ↓ 人工審稿

每天 10:00 / 19:30
publish.py
  → 從 Notion 取得「核准發布」的文章
  → 依序發布主文 → 留言1 → 留言2 到 Threads
  → 更新 Notion 狀態為「已發布」
```

---

## 內容策略

**帳號定位：** AI 與數據大師（銷售 AI 數據解決方案）

**6 大支柱：**
- 生產力提升
- 數位工具應用
- 會員經營
- AI 提示詞
- 數位轉型
- 自動化行銷

**內容類型比例：**
| 類型 | 比例 | 說明 |
|------|------|------|
| 純知識 / 方法論 | 60% | 實用知識分享 |
| 工具評測 / 比較 | 25% | 中立工具推薦 |
| 自家方案軟性露出 | 10% | 自然帶入品牌價值 |
| 硬性推廣 | 5% | 直接 CTA |

---

## 檔案結構

```
Auto Threads/
├── generate.py        # 每天 07:00 執行：AI 生成文章並建立到 Notion
├── publish.py         # 每天 10:00 / 19:30 執行：發布核准文章到 Threads
├── claude_service.py  # Gemini AI 生成邏輯
├── notion_service.py  # Notion 資料庫讀寫
├── threads_service.py # Threads API 發布邏輯
├── prompts.py         # AI Prompt 模板（各支柱 × 內容類型）
├── config.py          # 設定與常數
├── requirements.txt   # Python 套件相依
├── .env               # 機密金鑰（不進 git）
├── .env.example       # 金鑰格式範本
└── .github/workflows/
    ├── generate.yml   # GitHub Actions：每天 07:00 生成
    └── publish.yml    # GitHub Actions：每天 10:00 / 19:30 發布
```

---

## Notion 資料庫欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| 標題 | Title | AI 自動生成的貼文主題 |
| 支柱 | Select | 內容支柱分類 |
| 內容類型 | Select | 純知識 / 工具評測 / 軟性露出 / 硬推廣 |
| 預定發布日 | Date | 文章建立當天的日期（台灣時間） |
| 發布時間 | Select | `10:00` 或 `19:30` |
| 主文 | Text | AI 生成的主文（150–250 字） |
| 留言1 | Text | AI 生成的延伸內容或 Prompt 範本 |
| 審稿狀態 | Select | 見下方狀態流程 |
| 備註 | Text | 審稿者填寫修改意見（選填） |

**審稿狀態流程：**
```
待審核 → 核准發布 → 已發布
         ↓
       需修改（填備註後，隔天 07:00 自動重生成）
```

---

## 初次設定

### 1. 安裝環境

```bash
pip install -r requirements.txt
```

### 2. 設定金鑰

複製 `.env.example` 為 `.env`，填入以下金鑰：

```
NOTION_TOKEN=          # Notion Integration Token
NOTION_DATABASE_ID=    # Notion 資料庫 ID
GOOGLE_API_KEY=        # Google Gemini API Key
THREADS_USER_ID=       # Threads 帳號 User ID
THREADS_ACCESS_TOKEN=  # Threads Long-lived Access Token
```

#### 各金鑰取得方式

**Notion Token**
1. 前往 [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. 建立新的 Integration，複製 `Internal Integration Token`
3. 在 Notion 資料庫頁面右上角 → 連結 → 加入此 Integration

**Notion Database ID**
- 開啟 Notion 資料庫頁面，URL 格式為：
  `https://notion.so/yourworkspace/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...`
- 取 `?v=` 前的 32 字元即為 Database ID

**Google Gemini API Key**
1. 前往 [aistudio.google.com](https://aistudio.google.com)
2. 點選「Get API Key」→「Create API Key」

**Threads User ID & Access Token**
1. 前往 [developers.facebook.com](https://developers.facebook.com) → 你的 App
2. Threads API → API Setup → 產生 Long-lived Access Token
3. User ID 可在 API 回應或帳號設定中取得

> ⚠️ **注意：Threads Access Token 每 60 天過期**，需手動更新（見下方維護章節）

### 3. 設定 GitHub Actions Secrets

前往 GitHub repo → Settings → Secrets and variables → Actions → New repository secret

需新增以下 5 個 Secrets（名稱需完全一致）：

| Secret 名稱 | 對應 .env 欄位 |
|-------------|---------------|
| `NOTION_TOKEN` | NOTION_TOKEN |
| `NOTION_DATABASE_ID` | NOTION_DATABASE_ID |
| `GOOGLE_API_KEY` | GOOGLE_API_KEY |
| `THREADS_USER_ID` | THREADS_USER_ID |
| `THREADS_ACCESS_TOKEN` | THREADS_ACCESS_TOKEN |

---

## 日常操作

### 正常流程

1. 每天早上進 Notion，會看到兩篇新文章（狀態：待審核）
2. 點開文章，閱讀主文、留言1、留言2
3. 確認沒問題 → 將狀態改為 **核准發布**
4. 系統在 10:00 / 19:30 自動發布到 Threads

### 需要修改時

1. 將狀態改為 **需修改**
2. 在「備註」欄填寫修改意見（例如：「語氣太正式，改輕鬆一點」）
3. 隔天 07:00 系統會自動依備註重新生成，狀態改回「待審核」

### 手動觸發（測試用）

前往 GitHub repo → Actions → 選擇 workflow → Run workflow

---

## 排程時間

所有時間均為台灣時間（UTC+8）：

| 時間 | 動作 |
|------|------|
| 07:00 | generate.py：AI 生成今天兩篇文章 |
| 10:00 | publish.py：發布早上那篇 |
| 19:30 | publish.py：發布晚上那篇 |

---

## 維護

### Threads Access Token 更新（每 60 天）

Token 過期後發布會失敗，需手動更新：

1. 前往 [developers.facebook.com](https://developers.facebook.com) → 你的 App → Threads API
2. 重新產生 Long-lived Access Token
3. 更新 `.env` 檔案中的 `THREADS_ACCESS_TOKEN`
4. 更新 GitHub Secrets 中的 `THREADS_ACCESS_TOKEN`

> 建議每 50 天提醒自己更新一次，避免中途失效

### 查看執行 Log

前往 GitHub repo → Actions → 點選對應的執行記錄

### 調整 Prompt 或口吻

編輯 `prompts.py`：
- `SYSTEM_PROMPT`：全域口吻規則
- `AUTO_PILLAR_TEMPLATES`：各支柱的自動生成模板
- `PILLAR_TEMPLATES`：修改模式使用的模板

---

## 常見問題

**Q: 文章沒有生成？**
- 確認 GitHub Actions 的 generate.yml 有正常執行（Actions 頁面查看 log）
- 確認 GOOGLE_API_KEY 和 NOTION_TOKEN 的 Secrets 設定正確

**Q: 文章生成了但沒有發布？**
- 確認文章狀態已改為「核准發布」
- 確認 THREADS_ACCESS_TOKEN 未過期（最常見原因）
- 確認發布時間欄位填的是 `10:00` 或 `19:30`

**Q: 想改變每天發文的比例或支柱？**
- 編輯 `generate.py` 中的 `CONTENT_TYPE_WEIGHTS`（比例）
- 編輯 `generate.py` 中的 `PILLAR_BY_TYPE`（支柱清單）
