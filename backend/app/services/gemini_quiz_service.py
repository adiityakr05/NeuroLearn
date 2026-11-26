import json
import logging
from typing import List, Optional
import httpx
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings

logger = logging.getLogger("neurolearn.gemini_quiz")


class GeminiQuestionItem(BaseModel):
    question: str = Field(..., min_length=5)
    options: List[str] = Field(..., min_length=4, max_length=4)
    correct_answer: str = Field(..., min_length=1)
    explanation: str = Field(..., min_length=5)
    subject: str
    topic: str
    difficulty: str
    concept: str = "Core Concept"

    @field_validator("options")
    @classmethod
    def check_four_unique_options(cls, v: List[str]) -> List[str]:
        cleaned = [o.strip() for o in v if o and o.strip()]
        if len(cleaned) != 4:
            raise ValueError("Each question must have exactly 4 non-empty options.")
        return cleaned


class GeminiQuizPayload(BaseModel):
    questions: List[GeminiQuestionItem]


class GeminiQuizService:
    GEMINI_ENDPOINT_TEMPLATE = (
        "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    )

    @staticmethod
    def _build_prompt(subject: str, topic: str, difficulty: str, num_questions: int) -> str:
        return (
            f"Generate {num_questions} unique multiple-choice quiz questions for a university student.\n"
            f"Subject: {subject}\n"
            f"Topic: {topic}\n"
            f"Difficulty: {difficulty}\n\n"
            "Requirements:\n"
            "- Return ONLY valid JSON matching: "
            '{"questions": [{"question": "...", "options": ["A", "B", "C", "D"], '
            '"correct_answer": "exact text of one option", "explanation": "...", '
            f'"subject": "{subject}", "topic": "{topic}", "difficulty": "{difficulty}", "concept": "..."' + "}]}\n"
            "- Exactly 4 distinct options per question.\n"
            "- correct_answer MUST exactly match one of the 4 options.\n"
            "- No duplicate questions.\n"
        )

    async def generate_questions(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        num_questions: int,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[List[dict]]:
        key = (api_key if api_key is not None else settings.GEMINI_API_KEY).strip()
        if not key:
            return None

        chosen_model = (model or settings.GEMINI_MODEL or "gemini-2.5-flash").strip()
        url = self.GEMINI_ENDPOINT_TEMPLATE.format(model=chosen_model)
        prompt = self._build_prompt(subject, topic, difficulty, num_questions)

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.4,
            },
        }

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    resp = await client.post(
                        url,
                        params={"key": key},
                        json=body,
                    )
                if resp.status_code == 429:
                    logger.warning("Gemini API quota/rate limit reached (429).")
                    return None
                resp.raise_for_status()
                data = resp.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                parsed_raw = json.loads(text)
                validated = GeminiQuizPayload.model_validate(parsed_raw)

                seen = set()
                formatted = []
                for idx, q in enumerate(validated.questions):
                    q_norm = q.question.strip().lower()
                    if q_norm in seen:
                        continue
                    seen.add(q_norm)
                    try:
                        correct_idx = q.options.index(q.correct_answer.strip())
                    except ValueError:
                        correct_idx = 0
                    formatted.append({
                        "id": f"gemini_{idx + 1}",
                        "question": q.question.strip(),
                        "options": q.options,
                        "correctIndex": correct_idx,
                        "explanation": q.explanation.strip(),
                        "concept": q.concept,
                        "source": f"Google Gemini ({chosen_model})",
                    })
                if formatted:
                    return formatted[:num_questions]
            except (httpx.TimeoutException, httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
                logger.warning("Gemini quiz generation attempt %d failed: %s", attempt + 1, exc.__class__.__name__)
                continue
        return None


gemini_quiz_service = GeminiQuizService()
