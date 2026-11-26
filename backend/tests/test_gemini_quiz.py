import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.gemini_quiz_service import GeminiQuizService


@pytest.mark.asyncio
async def test_gemini_returns_none_when_key_missing():
    svc = GeminiQuizService()
    res = await svc.generate_questions("CPP", "Polymorphism", "Medium", 5, api_key="")
    assert res is None


@pytest.mark.asyncio
async def test_gemini_parses_valid_structured_json():
    svc = GeminiQuizService()
    mock_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "questions": [
                                    {
                                        "question": "What is runtime polymorphism in C++?",
                                        "options": [
                                            "Function overloading",
                                            "Virtual function overriding",
                                            "Template specialization",
                                            "Operator precedence",
                                        ],
                                        "correct_answer": "Virtual function overriding",
                                        "explanation": "Virtual functions resolve at runtime via vtable.",
                                        "subject": "CPP",
                                        "topic": "Polymorphism",
                                        "difficulty": "Medium",
                                        "concept": "vtable dispatch",
                                    }
                                ]
                            })
                        }
                    ]
                }
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        res = await svc.generate_questions("CPP", "Polymorphism", "Medium", 1, api_key="fake-key")
    assert res is not None
    assert len(res) == 1
    assert res[0]["correctIndex"] == 1
    assert "Google Gemini" in res[0]["source"]


@pytest.mark.asyncio
async def test_gemini_handles_quota_429_gracefully():
    svc = GeminiQuizService()
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        res = await svc.generate_questions("CPP", "Polymorphism", "Medium", 5, api_key="fake-key")
    assert res is None


@pytest.mark.asyncio
async def test_gemini_handles_timeout_gracefully():
    svc = GeminiQuizService()
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.TimeoutException("timeout"))):
        res = await svc.generate_questions("CPP", "Polymorphism", "Medium", 5, api_key="fake-key")
    assert res is None
