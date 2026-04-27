"""
generate.py — 每天 07:00 執行

功能：
1. 從 Notion 取得今天預定發布、尚未生成的貼文
2. 呼叫 Claude API 生成主文 / 留言1 / 留言2
3. 寫回 Notion，狀態設為「待審核」
4. 同時處理「需修改」的貼文（備註不為空）

crontab 設定：
0 7 * * * cd /path/to/Auto\ Threads && python generate.py >> logs/generate.log 2>&1
"""

import sys
from datetime import date
from notion_service import NotionService
from claude_service import ClaudeService


def run():
    notion = NotionService()
    claude = ClaudeService()

    today = date.today().isoformat()
    print(f"\n{'='*50}")
    print(f"[generate] 執行日期：{today}")
    print(f"{'='*50}")

    # ── 1. 生成今天的新貼文 ──────────────────────────────────
    drafts = notion.get_todays_drafts()
    print(f"\n[generate] 找到 {len(drafts)} 篇待生成貼文")

    for post in drafts:
        print(f"\n  處理：{post['title']} ({post['pillar']} / {post['content_type']})")
        try:
            main_post, comment1, comment2 = claude.generate_post(
                pillar=post["pillar"],
                content_type=post["content_type"],
                title=post["title"],
            )
            notion.update_generated_content(
                page_id=post["page_id"],
                main_post=main_post,
                comment1=comment1,
                comment2=comment2,
            )
            print(f"  ✓ 生成完成，已寫入 Notion（狀態：待審核）")
            _preview(main_post, comment1, comment2)
        except Exception as e:
            print(f"  ✗ 生成失敗：{e}", file=sys.stderr)

    # ── 2. 重新生成「需修改」的貼文 ──────────────────────────
    revision_posts = notion.get_needs_revision_posts()
    print(f"\n[generate] 找到 {len(revision_posts)} 篇需修改貼文")

    for post in revision_posts:
        print(f"\n  修改：{post['title']} | 備註：{post['notes']}")
        try:
            notion.clear_for_revision(post["page_id"])
            main_post, comment1, comment2 = claude.generate_post(
                pillar=post["pillar"],
                content_type=post["content_type"],
                title=post["title"],
                notes=post["notes"],
            )
            notion.update_generated_content(
                page_id=post["page_id"],
                main_post=main_post,
                comment1=comment1,
                comment2=comment2,
            )
            print(f"  ✓ 修改完成，已寫入 Notion（狀態：待審核）")
            _preview(main_post, comment1, comment2)
        except Exception as e:
            print(f"  ✗ 修改失敗：{e}", file=sys.stderr)

    print(f"\n[generate] 完成\n")


def _preview(main_post: str, comment1: str, comment2: str):
    """在 log 裡印出貼文預覽（前 100 字）"""
    preview = main_post[:100].replace("\n", " ")
    print(f"  預覽：{preview}...")
    if comment1:
        print(f"  留言1：{comment1[:60].replace(chr(10), ' ')}...")
    print(f"  留言2：{comment2[:80].replace(chr(10), ' ')}")


if __name__ == "__main__":
    run()
