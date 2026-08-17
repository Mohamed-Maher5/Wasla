# This file contains the conversational guidance for Wasla's customer calls.
# It keeps the support verification experience aligned with Egyptian Arabic customer conversations.

import requests

from app.shared.config import settings


CLASSIFICATION_SYSTEM_PROMPT = """You classify a customer's spoken response in Egyptian Arabic during a
support call, where they were asked whether their previously reported
problem is resolved. Reply with EXACTLY one word, nothing else: resolved,
off_topic, unclear, or not_resolved.
- resolved: they clearly confirm the issue is fixed
- not_resolved: they clearly confirm the issue is NOT fixed
- off_topic: they're responding but not actually answering the yes/no
  question (talking about something else, unrelated complaints, etc.)
- unclear: speech was too garbled/short/ambiguous to tell any of the above"""

EXPECTED_OUTCOMES = {"resolved", "off_topic", "unclear", "not_resolved"}
GROQ_MODEL = "openai/gpt-oss-20b"
GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


def classify_response(transcript: str) -> str:
    if not transcript.strip():
        return "unclear"

    if not settings.groq_llm_api_key:
        print("classify_response ERROR: LLM API key is not configured")
        return "unclear"

    try:
        response = requests.post(
            GROQ_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {settings.groq_llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": transcript},
                ],
                "temperature": 0,
                "max_completion_tokens": 128,
                "reasoning_effort": "low",
                "include_reasoning": False,
            },
            timeout=6,
        )
        response.raise_for_status()
        raw_result = response.json()["choices"][0]["message"]["content"]
        result = raw_result.strip().lower().strip("`'\".،,;:!؟? ")
    except Exception as exc:
        response_body = getattr(getattr(exc, "response", None), "text", "")
        if response_body:
            print(f"classify_response ERROR: {exc} response_body={response_body}")
        else:
            print(f"classify_response ERROR: {exc}")
        return "unclear"

    if result not in EXPECTED_OUTCOMES:
        print(f"classify_response ERROR: unexpected LLM response={result!r}")
        return "unclear"

    return result
