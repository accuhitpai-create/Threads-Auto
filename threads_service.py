import re
import time
import requests
from config import THREADS_USER_ID, THREADS_ACCESS_TOKEN, THREADS_API_BASE

THREADS_CHAR_LIMIT = 500


def strip_markdown(text: str) -> str:
    """移除 Threads 不支援的 Markdown 符號，保留 ``` 程式碼區塊內容"""
    # 先保護 ``` 程式碼區塊（留言1 的 Prompt 範本要保留）
    code_blocks = []
    def _stash(m):
        code_blocks.append(m.group(0))
        return f"\x00CODE{len(code_blocks)-1}\x00"
    text = re.sub(r"```[\s\S]*?```", _stash, text)

    # 移除 **粗體** 與 __粗體__
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    # 移除 *斜體* 與 _斜體_（避免誤傷一般文字，只處理成對出現）
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", text)
    # 移除行首的 # 標題、> 引用、- 項目
    text = re.sub(r"^\s*#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-+]\s+", "● ", text, flags=re.MULTILINE)
    # 移除 `行內程式碼` 的反引號
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # 還原程式碼區塊
    for i, block in enumerate(code_blocks):
        text = text.replace(f"\x00CODE{i}\x00", block)

    return text.strip()


class ThreadsService:
    def __init__(self):
        self.user_id = THREADS_USER_ID
        self.token = THREADS_ACCESS_TOKEN

    def publish_post_with_comments(
        self,
        main_post: str,
        comment1: str = "",
        comment2: str = ""
    ) -> str:
        """
        發布主文 + 留言1（可能多則）+ 留言2
        回傳主文的 post_id
        """
        # 先清除 Markdown 符號（Threads 不支援）
        main_post = strip_markdown(main_post)
        comment1 = strip_markdown(comment1)
        comment2 = strip_markdown(comment2)

        # 主文（超過 500 字也切分成主文 + 續文）
        main_chunks = self._split_text(main_post, THREADS_CHAR_LIMIT)
        post_id = self._publish_text(main_chunks[0])
        print(f"  ✓ 主文發布成功：{post_id}")
        time.sleep(2)

        # 主文太長時，後續段落以回覆形式接上去
        for i, chunk in enumerate(main_chunks[1:], 1):
            rid = self._publish_reply(chunk, reply_to_id=post_id)
            print(f"  ✓ 主文續文 {i}：{rid}")
            time.sleep(2)

        # 留言1（可能需要切成多則）
        if comment1.strip():
            chunks = self._split_text(comment1, THREADS_CHAR_LIMIT)
            for i, chunk in enumerate(chunks, 1):
                rid = self._publish_reply(chunk, reply_to_id=post_id)
                print(f"  ✓ 留言1 ({i}/{len(chunks)})：{rid}")
                time.sleep(2)

        # 留言2（CTA，一般不會超過 500）
        if comment2.strip():
            chunks = self._split_text(comment2, THREADS_CHAR_LIMIT)
            for i, chunk in enumerate(chunks, 1):
                rid = self._publish_reply(chunk, reply_to_id=post_id)
                print(f"  ✓ 留言2 ({i}/{len(chunks)})：{rid}")
                time.sleep(2)

        return post_id

    # ── 內部方法 ──────────────────────────────────────────────

    def _split_text(self, text: str, limit: int) -> list[str]:
        """把長文字切成多段，每段不超過 limit 字元。優先在段落與句子邊界切。"""
        text = text.strip()
        if len(text) <= limit:
            return [text]

        chunks = []
        remaining = text

        while len(remaining) > limit:
            # 優先在換行處切
            split_at = remaining.rfind("\n\n", 0, limit)
            if split_at == -1:
                split_at = remaining.rfind("\n", 0, limit)
            if split_at == -1:
                # 找句號、問號、驚嘆號
                for punct in ["。", "？", "！", "．", ".", "!", "?"]:
                    pos = remaining.rfind(punct, 0, limit)
                    if pos > split_at:
                        split_at = pos + 1
            if split_at <= 0:
                split_at = limit

            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()

        if remaining:
            chunks.append(remaining)
        return chunks

    def _create_container(self, text: str, reply_to_id: str = None) -> str:
        """建立媒體容器，回傳 container_id。用 POST body 傳遞，避免 URL 過長。"""
        url = f"{THREADS_API_BASE}/{self.user_id}/threads"
        data = {
            "media_type": "TEXT",
            "text": text,
            "access_token": self.token,
        }
        if reply_to_id:
            data["reply_to_id"] = reply_to_id

        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()["id"]

    def _publish_container(self, container_id: str) -> str:
        """發布容器，回傳 post_id"""
        url = f"{THREADS_API_BASE}/{self.user_id}/threads_publish"
        data = {
            "creation_id": container_id,
            "access_token": self.token,
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()["id"]

    def _publish_text(self, text: str) -> str:
        """建立並發布一則文字貼文"""
        container_id = self._create_container(text)
        time.sleep(1)
        return self._publish_container(container_id)

    def _publish_reply(self, text: str, reply_to_id: str) -> str:
        """建立並發布一則回覆"""
        container_id = self._create_container(text, reply_to_id=reply_to_id)
        time.sleep(1)
        return self._publish_container(container_id)
