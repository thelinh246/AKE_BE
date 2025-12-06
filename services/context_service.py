from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import List, Tuple

import google.generativeai as genai

from config import GEMINI_MODEL, GOOGLE_API_KEY

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model():
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is required for context rewrite.")
    genai.configure(api_key=GOOGLE_API_KEY)
    return genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=(
            "Bạn là trợ lý tóm tắt và viết lại câu hỏi cho chatbot tư vấn du học/visa Úc. "
            "Luôn trả JSON với các key: rewritten_question, new_title."
            "Phản hổi trả về không được chứa định dạng json code block."
        ),
    )


def rewrite_question_with_context(
    current_title: str | None,
    history: List[str],
    new_question: str,
) -> Tuple[str, str]:
    """
    Dựa trên title hiện tại + history + câu hỏi mới, viết lại câu hỏi và đề xuất title mới.

    Returns:
        rewritten_question: câu hỏi đã viết lại (fallback = new_question)
        new_title: tiêu đề gợi ý (fallback = current_title or cắt từ question)
    """
    prompt = f"""
Bạn sẽ nhận:
- Title hiện tại: "{current_title or ''}"
- Lịch sử: {history}
- Câu hỏi mới: "{new_question}"

Nhiệm vụ:
1) Viết lại câu hỏi mới sao cho tự chứa ngữ cảnh (nếu title/historry có ích).
2) Đề xuất title ngắn gọn (<= 60 ký tự) tóm tắt cuộc hội thoại.

Chỉ trả về JSON với đúng hai key không bao gồm ```json ... ```:
{{
  "rewritten_question": "...",
  "new_title": "..."
}}
"""
    model = _get_model()
    try:
        response = model.generate_content(prompt)
        print("Gemini rewrite response:", response)
        raw_text = (getattr(response, "text", "") or "").strip()
        if not raw_text:
            raise ValueError("Empty response from Gemini rewrite.")
        data = json.loads(raw_text)
        rewritten = data.get("rewritten_question") or new_question
        new_title = data.get("new_title") or current_title or new_question[:60]
        logger.info(
            "rewrite_question_with_context: success",
            extra={
                "current_title": current_title,
                "new_title": new_title,
                "rewritten_question": rewritten,
            },
        )
        print(f"Rewritten question: {rewritten}")
        print(f"Suggested title: {new_title}")
        return rewritten, new_title
    except Exception:
        logger.warning(
            "rewrite_question_with_context: fallback",
            exc_info=True,
            extra={
                "current_title": current_title,
                "raw_response": locals().get("raw_text", "")[:500],
            },
        )
        return new_question, (current_title or new_question[:60])
