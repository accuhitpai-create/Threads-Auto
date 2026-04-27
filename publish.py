"""
publish.py — 每 15 分鐘執行

功能：
1. 從 Notion 取得「核准發布」且發布時間已到的貼文
2. 依序發布主文 → 留言1 → 留言2 到 Threads
3. 發布成功後將 Notion 狀態更新為「已發布」

crontab 設定：
0 10 * * * cd /path/to/Auto\ Threads && python publish.py >> logs/publish.log 2>&1
30 19 * * * cd /path/to/Auto\ Threads && python publish.py >> logs/publish.log 2>&1
"""

import sys
from datetime import datetime
from notion_service import NotionService
from threads_service import ThreadsService


def run():
    notion = NotionService()
    threads = ThreadsService()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n[publish] 執行時間：{now}")

    approved_posts = notion.get_approved_posts()
    print(f"[publish] 找到 {len(approved_posts)} 篇待發布貼文")

    if not approved_posts:
        print("[publish] 無待發布貼文，結束\n")
        return

    for post in approved_posts:
        print(f"\n  發布：{post['title']} ({post['publish_time']})")
        try:
            post_id = threads.publish_post_with_comments(
                main_post=post["main_post"],
                comment1=post["comment1"],
                comment2=post["comment2"],
            )
            notion.mark_as_published(post["page_id"])
            print(f"  ✓ 發布完成，Threads post_id：{post_id}")
        except Exception as e:
            print(f"  ✗ 發布失敗：{e}", file=sys.stderr)

    print(f"\n[publish] 完成\n")


if __name__ == "__main__":
    run()
