from datetime import date, datetime
from notion_client import Client
from config import (
    NOTION_TOKEN, NOTION_DATABASE_ID, NOTION_PROPS,
    STATUS_PENDING, STATUS_APPROVED, STATUS_PUBLISHED
)


class NotionService:
    def __init__(self):
        self.client = Client(auth=NOTION_TOKEN)
        self.db_id = NOTION_DATABASE_ID

    # ── 讀取 ──────────────────────────────────────────────────

    def get_todays_drafts(self) -> list[dict]:
        """取得今天預定發布、主文尚未生成的貼文"""
        today = date.today().isoformat()
        response = self.client.databases.query(
            database_id=self.db_id,
            filter={
                "and": [
                    {
                        "property": NOTION_PROPS["publish_date"],
                        "date": {"equals": today}
                    },
                    {
                        "property": NOTION_PROPS["main_post"],
                        "rich_text": {"is_empty": True}
                    }
                ]
            }
        )
        return [self._parse_page(p) for p in response.get("results", [])]

    def get_approved_posts(self) -> list[dict]:
        """取得核准發布、今天預定發布、時間已到的貼文"""
        today = date.today().isoformat()
        now_time = datetime.now().strftime("%H:%M")

        response = self.client.databases.query(
            database_id=self.db_id,
            filter={
                "and": [
                    {
                        "property": NOTION_PROPS["status"],
                        "select": {"equals": STATUS_APPROVED}
                    },
                    {
                        "property": NOTION_PROPS["publish_date"],
                        "date": {"equals": today}
                    }
                ]
            }
        )

        posts = []
        for page in response.get("results", []):
            parsed = self._parse_page(page)
            # 檢查發布時間是否已到
            if parsed.get("publish_time", "99:99") <= now_time:
                posts.append(parsed)
        return posts

    def get_needs_revision_posts(self) -> list[dict]:
        """取得標記為需修改的貼文（備註不為空）"""
        response = self.client.databases.query(
            database_id=self.db_id,
            filter={
                "and": [
                    {
                        "property": NOTION_PROPS["status"],
                        "select": {"equals": "需修改"}
                    },
                    {
                        "property": NOTION_PROPS["notes"],
                        "rich_text": {"is_not_empty": True}
                    }
                ]
            }
        )
        return [self._parse_page(p) for p in response.get("results", [])]

    # ── 寫入 ──────────────────────────────────────────────────

    def update_generated_content(
        self,
        page_id: str,
        main_post: str,
        comment1: str,
        comment2: str
    ):
        """將 AI 生成的貼文內容寫回 Notion，並設為待審核"""
        # 1. 更新屬性欄位（供自動化流程讀取）
        self.client.pages.update(
            page_id=page_id,
            properties={
                NOTION_PROPS["main_post"]: {
                    "rich_text": [{"text": {"content": main_post[:2000]}}]
                },
                NOTION_PROPS["comment1"]: {
                    "rich_text": [{"text": {"content": comment1[:2000]}}]
                },
                NOTION_PROPS["comment2"]: {
                    "rich_text": [{"text": {"content": comment2[:2000]}}]
                },
                NOTION_PROPS["status"]: {
                    "select": {"name": STATUS_PENDING}
                },
            }
        )
        # 2. 把內容也寫進頁面內文（方便審稿）
        self._write_page_body(page_id, main_post, comment1, comment2)

    def _write_page_body(
        self, page_id: str, main_post: str, comment1: str, comment2: str
    ):
        """在 Notion 頁面內文區顯示完整貼文（方便閱讀與編輯）"""
        # 先清空舊的內文
        existing = self.client.blocks.children.list(block_id=page_id)
        for block in existing.get("results", []):
            try:
                self.client.blocks.delete(block_id=block["id"])
            except Exception:
                pass

        blocks = []
        blocks.append(self._heading("📝 主文"))
        blocks.extend(self._paragraphs(main_post))

        if comment1.strip():
            blocks.append(self._heading("💬 留言 1"))
            blocks.extend(self._paragraphs(comment1))

        if comment2.strip():
            blocks.append(self._heading("🔗 留言 2（CTA）"))
            blocks.extend(self._paragraphs(comment2))

        self.client.blocks.children.append(block_id=page_id, children=blocks)

    def _heading(self, text: str) -> dict:
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            }
        }

    def _paragraphs(self, text: str) -> list[dict]:
        """把長文字切成多段 paragraph block（每段最多 1800 字）"""
        paragraphs = []
        for para in text.split("\n"):
            # Notion 單一 block 限 2000 字
            chunk = para[:1800] if para else ""
            paragraphs.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}] if chunk else []
                }
            })
        return paragraphs

    def mark_as_published(self, page_id: str):
        """發布成功後更新狀態"""
        self.client.pages.update(
            page_id=page_id,
            properties={
                NOTION_PROPS["status"]: {
                    "select": {"name": STATUS_PUBLISHED}
                }
            }
        )

    def clear_for_revision(self, page_id: str):
        """清空主文讓 AI 重新生成（備註保留供 AI 參考）"""
        self.client.pages.update(
            page_id=page_id,
            properties={
                NOTION_PROPS["main_post"]: {
                    "rich_text": []
                },
                NOTION_PROPS["comment1"]: {
                    "rich_text": []
                },
                NOTION_PROPS["comment2"]: {
                    "rich_text": []
                },
            }
        )

    # ── 解析 ──────────────────────────────────────────────────

    def _parse_page(self, page: dict) -> dict:
        props = page["properties"]

        def get_text(prop_name):
            prop = props.get(prop_name, {})
            rich_text = prop.get("rich_text", [])
            return rich_text[0]["text"]["content"] if rich_text else ""

        def get_title(prop_name):
            prop = props.get(prop_name, {})
            title = prop.get("title", [])
            return title[0]["text"]["content"] if title else ""

        def get_select(prop_name):
            prop = props.get(prop_name, {})
            select = prop.get("select")
            return select["name"] if select else ""

        def get_date(prop_name):
            prop = props.get(prop_name, {})
            date_val = prop.get("date")
            return date_val["start"] if date_val else ""

        return {
            "page_id": page["id"],
            "title": get_title(NOTION_PROPS["title"]),
            "pillar": get_select(NOTION_PROPS["pillar"]),
            "content_type": get_select(NOTION_PROPS["content_type"]),
            "publish_date": get_date(NOTION_PROPS["publish_date"]),
            "publish_time": get_select(NOTION_PROPS["publish_time"]),
            "main_post": get_text(NOTION_PROPS["main_post"]),
            "comment1": get_text(NOTION_PROPS["comment1"]),
            "comment2": get_text(NOTION_PROPS["comment2"]),
            "status": get_select(NOTION_PROPS["status"]),
            "notes": get_text(NOTION_PROPS["notes"]),
        }
