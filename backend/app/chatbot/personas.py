# Persona presets: chosen once per conversation (by the agent/admin, via the
# chat UI dropdown) and baked into that conversation's system prompt for
# every turn. Adding a new persona = adding one entry here; nothing else
# needs to change.
#
# Each value is a short instruction appended to the base system prompt in
# service._generate_answer — it should describe TONE and FRAMING only.
# The hard rules (only answer from provided context, language matching,
# citation format, the NO_KB_MATCH marker) stay in the base prompt and are
# never overridden by a persona.

PERSONAS: dict[str, dict[str, str]] = {
    "general": {
        "label": "عام (افتراضي)",
        "instruction": (
            "Respond as a neutral, helpful support assistant with no "
            "particular department framing."
        ),
    },
    "it_support": {
        "label": "دعم فني (IT)",
        "instruction": (
            "Respond as an IT support specialist. Use precise technical "
            "language when the source material is technical, prefer "
            "numbered step-by-step instructions for how-to questions, and "
            "flag anything that sounds like it needs escalation to a "
            "system administrator."
        ),
    },
    "hr": {
        "label": "موارد بشرية (HR)",
        "instruction": (
            "Respond as an HR support specialist. Use a warm, formal, and "
            "discreet tone appropriate for policy, benefits, and workplace "
            "questions. Where the source material gives an official "
            "policy, quote its practical effect plainly rather than "
            "legal wording."
        ),
    },
    "sales": {
        "label": "مبيعات (Sales)",
        "instruction": (
            "Respond as a sales support specialist. Use an upbeat, "
            "customer-facing tone, highlight concrete numbers (pricing, "
            "specs, timelines) when they appear in the source material, "
            "and keep answers brief enough to relay directly to a client."
        ),
    },
}

DEFAULT_PERSONA = "general"


def resolve_persona(persona: str | None) -> str:
    """Falls back to the default for anything unrecognized, so a bad/old
    client value never breaks a conversation."""
    if persona and persona in PERSONAS:
        return persona
    return DEFAULT_PERSONA


def persona_instruction(persona: str) -> str:
    return PERSONAS[resolve_persona(persona)]["instruction"]
