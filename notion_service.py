from datetime import datetime, timezone, timedelta

TWN = timezone(timedelta(hours=8))
from notion_client import Client
from config import (
    NOTION_TOKEN, NOTION_DATABASE_ID, NOTION_PROPS,
    STATUS_PENDING, STATUS_APPROVED, STATUS_PUBLISHED
)


class NotionService:
    def __init__(self):
        self.client = Client(auth=NOTION_TOKEN)
        self.db_id = NOTION_DATABASE_ID
        db = self.client.databases.retrieve(database_id=self.db_id)
        self._db_props = set(db["properties"].keys())

    # ── 讀取 ──────────────────────────────────────────────────

    def get_approved_posts(self) -> list[dict]:
        """取得核准發布、今天預定發布、時間已到的貼文"""
        now_twn = datetime.now(TWN)
        today = now_twn.date().isoformat()
        now_time = now_twn.strftime("%H:%M")

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

    def create_post(
        self,
        title: str,
        pillar: str,
        content_type: str,
        publish_date: str,
        publish_time: str,
        main_post: str,
        comment1: str,
        comment2: str,
    ) -> str:
        """在 Notion 建立新貼文頁面，回傳 page_id"""
        properties = {
            NOTION_PROPS["title"]: {
                "title": [{"text": {"content": title}}]
            },
            NOTION_PROPS["pillar"]: {
                "select": {"name": pillar}
            },
            NOTION_PROPS["content_type"]: {
                "select": {"name": content_type}
            },
            NOTION_PROPS["publish_date"]: {
                "date": {"start": publish_date}
            },
            NOTION_PROPS["publish_time"]: {
                "select": {"name": publish_time}
            },
            NOTION_PROPS["main_post"]: {
                "rich_text": [{"text": {"content": main_post[:2000]}}]
            },
            NOTION_PROPS["status"]: {
                "select": {"name": STATUS_PENDING}
            },
        }
        if NOTION_PROPS["comment1"] in self._db_props and comment1:
            properties[NOTION_PROPS["comment1"]] = {
                "rich_text": [{"text": {"content": comment1[:2000]}}]
            }
        if NOTION_PROPS["comment2"] in self._db_props and comment2:
            properties[NOTION_PROPS["comment2"]] = {
                "rich_text": [{"text": {"content": comment2[:2000]}}]
            }

        page = self.client.pages.create(
            parent={"database_id": self.db_id},
            properties=properties,
        )
        page_id = page["id"]
        self._write_page_body(page_id, main_post, comment1, comment2)
        return page_id

    def update_generated_content(
        self,
        page_id: str,
        main_post: str,
        comment1: str,
        comment2: str
    ):
        """將 AI 生成的貼文內容寫回 Notion，並設為待審核"""
        props = {
            NOTION_PROPS["main_post"]: {
                "rich_text": [{"text": {"content": main_post[:2000]}}]
            },
            NOTION_PROPS["status"]: {
                "select": {"name": STATUS_PENDING}
            },
        }
        if NOTION_PROPS["comment1"] in self._db_props:
            props[NOTION_PROPS["comment1"]] = {
                "rich_text": [{"text": {"content": comment1[:2000]}}]
            }
        if NOTION_PROPS["comment2"] in self._db_props:
            props[NOTION_PROPS["comment2"]] = {
                "rich_text": [{"text": {"content": comment2[:2000]}}]
            }

        self.client.pages.update(page_id=page_id, properties=props)
        self._write_page_body(page_id, main_post, comment1, comment2)

    def _write_page_body(
        self, page_id: str, main_post: str, comment1: str, comment2: str
    ):
        """在 Notion 頁面內文區顯示完整貼文（方便閱讀與編輯）"""
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
        paragraphs = []
        for para in text.split("\n"):
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
        props = {
            NOTION_PROPS["main_post"]: {"rich_text": []},
        }
        if NOTION_PROPS["comment1"] in self._db_props:
            props[NOTION_PROPS["comment1"]] = {"rich_text": []}
        if NOTION_PROPS["comment2"] in self._db_props:
            props[NOTION_PROPS["comment2"]] = {"rich_text": []}
        self.client.pages.update(page_id=page_id, properties=props)

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
