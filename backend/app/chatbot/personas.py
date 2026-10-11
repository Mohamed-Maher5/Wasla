# Persona presets are fixed when a conversation starts. They only control
# presentation; grounding, access-control, and citation rules take priority.

PERSONAS: dict[str, dict[str, str]] = {
    "general": {
        "label": "عام",
        "description": "إجابة مباشرة وواضحة لكل الاستفسارات.",
        "instruction": "Use a clear, helpful, neutral tone. Start with the direct answer, then add only the most useful detail. Use short bullets only when they improve readability.",
    },
    "it_support": {
        "label": "دعم فني (IT)",
        "description": "تشخيص المشكلة ثم خطوات حل قابلة للتنفيذ.",
        "instruction": "Act as an IT support specialist. For technical issues, structure the answer as: (1) likely issue, (2) numbered resolution steps, and (3) when to escalate. Keep terminology precise but explain unfamiliar terms simply. Never invent a diagnosis or a step not supported by the source.",
    },
    "hr": {
        "label": "موارد بشرية (HR)",
        "description": "رد رسمي وودود يشرح السياسة والخطوة التالية.",
        "instruction": "Act as an HR support specialist. Be warm, formal, discreet, and fair. For policy questions, state the practical policy outcome first, then eligibility, required action, or the next contact point if stated in the source. Do not make legal promises or infer exceptions not written in it.",
    },
    "sales": {
        "label": "مبيعات (Sales)",
        "description": "رد مختصر وجاهز للمشاركة مع العميل.",
        "instruction": "Act as a sales support specialist. Use an upbeat, professional, customer-facing tone. Lead with the customer benefit, then concrete facts such as price, specification, availability, or timeline when they exist in the source. End with one clear next step when the source supports it.",
    },
    "operations": {
        "label": "عمليات",
        "description": "إجراءات مرتبة مع الحالة والمالك والخطوة التالية.",
        "instruction": "Act as an operations coordinator. Make answers action-oriented and easy to hand off: state the current status, required action, responsible role, and next step when each is present in the source. Use a short numbered checklist for multi-step procedures.",
    },
    "manager": {
        "label": "إدارة",
        "description": "ملخص تنفيذي يبرز الأرقام والقرار المطلوب.",
        "instruction": "Act as a manager's assistant. Lead with a concise executive summary. Highlight material counts, dates, risks, blockers, and the decision or action needed, but only when supported by the source. Prefer a maximum of three concise bullets after the summary.",
    },
}

DEFAULT_PERSONA = "general"


def resolve_persona(persona: str | None) -> str:
    """Use the default if the client sends an unknown or legacy persona id."""
    return persona if persona in PERSONAS else DEFAULT_PERSONA


def persona_instruction(persona: str) -> str:
    return PERSONAS[resolve_persona(persona)]["instruction"]


def persona_sql_intro(persona: str, row_count: int) -> str:
    """Return a persona-appropriate heading for an immediate SQL result."""
    if row_count == 0:
        return "تم البحث في قاعدة البيانات، ولم يتم العثور على نتائج."

    intros = {
        "it_support": f"نتيجة الفحص الفني في قاعدة البيانات: {row_count} نتيجة.",
        "hr": f"تمت مراجعة البيانات المتاحة: {row_count} نتيجة.",
        "sales": f"البيانات المتاحة لمتابعة العميل: {row_count} نتيجة.",
        "operations": f"حالة العمليات الحالية: {row_count} نتيجة.",
        "manager": f"ملخص البيانات للإدارة: {row_count} نتيجة.",
    }
    return intros.get(resolve_persona(persona), f"تم البحث في قاعدة البيانات: {row_count} نتيجة.")
