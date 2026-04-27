"""
generate.py — 每天 07:00 執行

功能：
1. 依照支柱比例（60/25/10/5）隨機選出兩組「支柱 + 內容類型」
2. 呼叫 Gemini AI 自動生成標題 + 主文 / 留言1 / 留言2
3. 在 Notion 建立兩篇新文章（發布時間分別為 10:00 / 19:30），狀態設為「待審核」
4. 同時處理「需修改」的貼文（備註不為空）

crontab 設定：
0 7 * * * cd /path/to/Auto\ Threads && python generate.py >> logs/generate.log 2>&1
"""

import sys
import random
from datetime import date
from notion_service import NotionService
from claude_service import ClaudeService

# 內容類型比例（60/25/10/5）
CONTENT_TYPE_WEIGHTS = [
    ("純知識",  60),
    ("工具評測", 25),
    ("軟性露出", 10),
    ("硬推廣",   5),
]

# 各內容類型可用的支柱
PILLAR_BY_TYPE = {
    "純知識":  ["生產力提升", "數位工具應用", "會員經營", "AI提示詞", "數位轉型", "自動化行銷"],
    "工具評測": ["生產力提升", "數位工具應用"],
    "軟性露出": ["會員經營", "自動化行銷"],
    "硬推廣":  ["綜合"],
}

PUBLISH_TIMES = ["10:00", "19:30"]


def pick_combination(exclude_pillar=None):
    types, weights = zip(*CONTENT_TYPE_WEIGHTS)
    content_type = random.choices(types, weights=weights, k=1)[0]
    pillars = [p for p in PILLAR_BY_TYPE[content_type] if p != exclude_pillar]
    if not pillars:
        pillars = PILLAR_BY_TYPE[content_type]
    pillar = random.choice(pillars)
    return pillar, content_type


def run():
    notion = NotionService()
    claude = ClaudeService()

    today = date.today().isoformat()
    print(f"\n{'='*50}")
    print(f"[generate] 執行日期：{today}")
    print(f"{'='*50}")

    # ── 1. 自動生成今天兩篇 ──────────────────────────────────
    first_pillar = None
    for i, publish_time in enumerate(PUBLISH_TIMES):
        pillar, content_type = pick_combination(exclude_pillar=first_pillar)
        first_pillar = pillar
        print(f"\n  [{i+1}/2] {pillar} / {content_type} → {publish_time}")
        try:
            title, main_post, comment1, comment2 = claude.generate_post(
                pillar=pillar,
                content_type=content_type,
            )
            notion.create_post(
                title=title,
                pillar=pillar,
                content_type=content_type,
                publish_date=today,
                publish_time=publish_time,
                main_post=main_post,
                comment1=comment1,
                comment2=comment2,
            )
            print(f"  ✓ 標題：{title}")
            print(f"  預覽：{main_post[:80].replace(chr(10), ' ')}...")
        except Exception as e:
            print(f"  ✗ 失敗：{e}", file=sys.stderr)

    # ── 2. 重新生成「需修改」的貼文 ──────────────────────────
    revision_posts = notion.get_needs_revision_posts()
    print(f"\n[generate] 找到 {len(revision_posts)} 篇需修改貼文")

    for post in revision_posts:
        print(f"\n  修改：{post['title']} | 備註：{post['notes']}")
        try:
            notion.clear_for_revision(post["page_id"])
            _, main_post, comment1, comment2 = claude.generate_post(
                pillar=post["pillar"],
                content_type=post["content_type"],
                existing_title=post["title"],
                notes=post["notes"],
            )
            notion.update_generated_content(
                page_id=post["page_id"],
                main_post=main_post,
                comment1=comment1,
                comment2=comment2,
            )
            print(f"  ✓ 修改完成")
        except Exception as e:
            print(f"  ✗ 修改失敗：{e}", file=sys.stderr)

    print(f"\n[generate] 完成\n")


if __name__ == "__main__":
    run()
