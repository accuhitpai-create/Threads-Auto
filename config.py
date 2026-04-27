import os
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

THREADS_USER_ID = os.getenv("THREADS_USER_ID")
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
THREADS_API_BASE = "https://graph.threads.net/v1.0"

CONSULTATION_LINK = "https://www.accuhit.net/zhtw/contact"

# Notion 欄位名稱
NOTION_PROPS = {
    "title": "標題",
    "pillar": "支柱",
    "content_type": "內容類型",
    "publish_date": "預定發布日",
    "publish_time": "發布時間",
    "main_post": "主文",
    "comment1": "留言1",
    "comment2": "留言2",
    "status": "審稿狀態",
    "notes": "備註",
}

# 審稿狀態
STATUS_PENDING = "待審核"
STATUS_APPROVED = "核准發布"
STATUS_NEEDS_REVISION = "需修改"
STATUS_PUBLISHED = "已發布"
