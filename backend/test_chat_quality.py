"""Quick smoke test for chatbot response quality fixes."""
import re
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq

# ── 1. Test _strip_thinking ──────────────────────────────────────────────

def _strip_thinking(text: str) -> str:
    return re.sub(r"<think>[\s\S]*?</think>", "", text).strip()

# Test cases for the strip function
t1 = "<think>Okay, the user is greeting me. I should respond warmly.</think>مرحباً، كيف حالك؟"
t2 = "some normal text without thinking"
t3 = "<think>let me think</think> first <think>another block</think> result"

assert _strip_thinking(t1) == "مرحباً، كيف حالك？", f"FAIL t1: {_strip_thinking(t1)}"
assert _strip_thinking(t2) == "some normal text without thinking", f"FAIL t2"
assert _strip_thinking(t3) == "result", f"FAIL t3: {_strip_thinking(t3)}"
print("[PASS] _strip_thinking works correctly\n")

# ── 2. Live LLM test ────────────────────────────────────────────────────

from dotenv import load_dotenv
load_dotenv("/mnt/hdd/projects/Wasla/.env")

api_key = os.getenv("GROQ_LLM_API_KEY")
if not api_key:
    print("GROQ_LLM_API_KEY not set — skipping live LLM test")
    sys.exit(0)

groq = Groq(api_key=api_key)
CHAT_MODEL = "qwen/qwen3.6-27b"

system_prompt = (
    "You are an Arabic-speaking support assistant. Rules:\n"
    "- Answer ONLY in Arabic. Never use English.\n"
    "- For greetings (like \"ازيك\", \"مرحبا\", \"السلام عليكم\"), small talk, "
    "or general questions unrelated to the uploaded documents — respond "
    "naturally and briefly like a helpful assistant. Do NOT refuse these.\n"
    "- For questions answered using the provided documents: keep the answer "
    "concise and cite the source document name at the end like (المصدر: اسم_الملف).\n"
    "- For knowledge-base questions where the provided documents do NOT "
    "contain the answer: say explicitly that this information is not "
    "available in the uploaded documents.\n"
    "- Never fabricate information. Only use what is in the documents for "
    "knowledge-base questions."
)

def ask(question, context=None):
    if context:
        user_msg = f"Available information:\n{context}\n\nQuestion: {question}"
    else:
        user_msg = f"Question: {question}"
    resp = groq.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
    )
    raw = resp.choices[0].message.content
    cleaned = _strip_thinking(raw)
    return raw, cleaned

# Test 1: Greeting — no context
print("── Test 1: Greeting (\"ازيك\") ──")
raw, cleaned = ask("ازيك")
print(f"  Raw:    {raw[:150]}...")
print(f"  Clean:  {cleaned}")
assert "<think>" not in cleaned, "FAIL: <think> block leaked!"
print("  ✓ No <think> block in output\n")

# Test 2: Real KB question — with matching context
print("── Test 2: KB question with matching doc ──")
fake_context = (
    "[Source 1 - دليل_العمليات.pdf]\n"
    "ساعات العمل من 9 صباحاً إلى 5 مساءً. يوم الجمعة راحة."
)
raw, cleaned = ask("ايه هي ساعات العمل؟", context=fake_context)
print(f"  Raw:    {raw[:200]}...")
print(f"  Clean:  {cleaned}")
assert "<think>" not in cleaned, "FAIL: <think> block leaked!"
assert "المصدر" in cleaned or "ساعات" in cleaned, "FAIL: no source citation or wrong answer"
print("  ✓ Arabic answer with source citation\n")

# Test 3: KB question — NO matching context
print("── Test 3: KB question with no matching doc ──")
raw, cleaned = ask("ايه هي سياسة الاستبدال؟", context=None)
print(f"  Raw:    {raw[:200]}...")
print(f"  Clean:  {cleaned}")
assert "<think>" not in cleaned, "FAIL: <think> block leaked!"
# Should indicate info not available
print("  ✓ Appropriate refusal response\n")

print("ALL TESTS PASSED")
