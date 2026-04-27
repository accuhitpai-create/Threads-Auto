from google import genai
from google.genai import types
from config import GOOGLE_API_KEY, GEMINI_MODEL
from prompts import SYSTEM_PROMPT, get_prompt


class ClaudeService:
    def __init__(self):
        self.client = genai.Client(api_key=GOOGLE_API_KEY)

    def generate_post(
        self,
        pillar: str,
        content_type: str,
        title: str,
        notes: str = ""
    ) -> tuple[str, str, str]:
        """
        生成貼文三個區塊：主文、留言1、留言2
        回傳 (main_post, comment1, comment2)
        """
        user_prompt = get_prompt(pillar, content_type, title, notes)

        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=8000,
                temperature=0.8,
            )
        )

        import os
        if os.getenv("DEBUG_RAW"):
            print("\n----- RAW OUTPUT -----")
            print(response.text)
            print("----- END RAW -----\n")

        return self._parse_output(response.text)

    def _parse_output(self, raw: str) -> tuple[str, str, str]:
        """解析輸出的三個區塊"""
        main_post = ""
        comment1 = ""
        comment2 = ""

        sections = raw.split("===")

        for i, section in enumerate(sections):
            section = section.strip()
            if section.startswith("主文==="):
                main_post = section.replace("主文===", "").strip()
            elif section == "主文" and i + 1 < len(sections):
                main_post = sections[i + 1].strip()
            elif section.startswith("留言1==="):
                comment1 = section.replace("留言1===", "").strip()
            elif section == "留言1" and i + 1 < len(sections):
                comment1 = sections[i + 1].strip()
            elif section.startswith("留言2==="):
                comment2 = section.replace("留言2===", "").strip()
            elif section == "留言2" and i + 1 < len(sections):
                comment2 = sections[i + 1].strip()

        if not main_post:
            main_post = raw.strip()

        if comment1.strip() in ("無", ""):
            comment1 = ""

        return main_post, comment1, comment2
