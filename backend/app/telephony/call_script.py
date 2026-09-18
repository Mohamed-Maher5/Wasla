# This file contains the conversational guidance for Wasla's customer calls.
# It keeps the support verification experience aligned with Egyptian Arabic customer conversations.

import time

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
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 0.3


def classify_response(transcript: str) -> str:
    if not transcript.strip():
        return "unclear"

    if not settings.groq_llm_api_key:
        print("classify_response ERROR: LLM API key is not configured")
        return "unclear"

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
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
                    "max_tokens": 128,
                },
                timeout=5,
            )
            response.raise_for_status()
            raw_result = response.json()["choices"][0]["message"]["content"]
            result = raw_result.strip().lower().strip("`'\".،,;:!؟? ")

            if result not in EXPECTED_OUTCOMES:
                print(f"classify_response: unexpected LLM response={result!r}, retrying ({attempt}/{MAX_RETRIES})")
                last_error = f"unexpected response: {result!r}"
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
                return "unclear"

            return result

        except Exception as exc:
            response_body = getattr(getattr(exc, "response", None), "text", "")
            error_msg = f"{exc}" + (f" response_body={response_body}" if response_body else "")
            print(f"classify_response ERROR (attempt {attempt}/{MAX_RETRIES}): {error_msg}")
            last_error = error_msg
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
                continue

    print(f"classify_response: all {MAX_RETRIES} attempts failed, last error: {last_error}")
    return "unclear"
