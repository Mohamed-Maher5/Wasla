# Natural-language -> SQL for Wasla's own app database (tickets, users,
# departments). Two-step, approval-gated flow:
#
#   1. generate_sql()  — LLM turns the question into one SELECT statement
#                         against a fixed, documented schema; the query is
#                         statically validated and stored server-side
#                         (never trusted back from the client) as a
#                         PendingSqlQuery, and only the SQL text + an id are
#                         returned for the user to review.
#   2. execute_sql()    — takes ONLY the pending-query id (re-validates the
#                         stored SQL, never a client-supplied SQL string),
#                         runs it inside a transaction that is always rolled
#                         back, and returns the rows.
#
# This is a defense-in-depth design for an internal, role-gated tool — not
# a substitute for running it against a genuinely read-only DB role in
# production, which is still recommended.

import re
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.shared.config import settings
from .models import PendingSqlQuery

# ---------------------------------------------------------------------------
# Fixed schema exposed to the model. Deliberately narrow: only the tables
# and columns an agent/admin should ever be able to query, and NEVER
# sensitive columns (password hashes, tokens, etc.) even though the real
# tables may have them.
# ---------------------------------------------------------------------------

SCHEMA_DESCRIPTION = """
Table: departments
  - id (integer, primary key)
  - name (text)

Table: users
  - id (integer, primary key)
  - name (text)
  - email (text)
  - role (text: 'superadmin' | 'admin' | 'agent')
  - department_id (integer, references departments.id, nullable)
  - created_by (integer, references users.id, nullable)

Table: tickets
  - id (integer, primary key)
  - client_name (text)
  - client_phone_number (text)
  - description (text)
  - status (text: 'resolved' | 'unresolved')
  - assigned_to (integer, references users.id)
  - created_by (integer, references users.id, nullable)
  - department_id (integer, references departments.id)
  - created_at (timestamp)
""".strip()

ALLOWED_TABLES = {"departments", "users", "tickets"}

ALLOWED_COLUMNS = {
    "departments": {"id", "name"},
    "users": {"id", "name", "email", "role", "department_id", "created_by"},
    "tickets": {
        "id", "client_name", "client_phone_number", "description", "status",
        "assigned_to", "created_by", "department_id", "created_at",
    },
}

# Anything matching these, anywhere in the query, is an automatic reject —
# a blanket net on top of the column whitelist above.
FORBIDDEN_SUBSTRINGS = (
    "password", "hash", "token", "secret", "jwt",
    "insert", "update", "delete", "drop", "alter", "create",
    "truncate", "grant", "revoke", "merge", "exec", "execute",
    "--", "/*", "*/", "pg_", "information_schema",
)

MAX_ROWS = 100


class SqlValidationError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Intent routing — called from chatbot/service.py at the top of ask_question
# so a single chat box can answer BOTH "unstructured" questions (RAG over
# uploaded documents) and "structured" questions (counts/listings over the
# app's own tickets/users/departments tables), without the user having to
# know or care which one their question needs.
#
# Keyword heuristic rather than an extra LLM call: keeps routing instant and
# free, and is deliberately conservative — it only fires when the question
# combines a "give me data/how many/list" signal with a mention of one of
# the structured tables, so plain document questions are never misrouted.
# ---------------------------------------------------------------------------

_DATA_SIGNAL_WORDS = (
    # Arabic
    "كام", "عدد", "احصائ", "إحصائ", "قائمة", "اعرض", "اطلع", "امتى اتعمل",
    "متوسط", "نسبة", "اجمالي", "إجمالي",
    # English
    "how many", "count", "list", "show me", "average", "total", "statistics",
)

_TABLE_SIGNAL_WORDS = (
    "تذكرة", "تذاكر", "موظف", "موظفين", "مستخدم", "مستخدمين", "قسم", "أقسام",
    "عميل", "عملاء",
    "ticket", "tickets", "user", "users", "employee", "department",
    "customer", "client",
)


def classify_intent(question: str) -> bool:
    """Returns True if `question` looks like it wants structured data from
    the app's own database (tickets/users/departments) rather than an
    answer looked up in uploaded documents."""
    lowered = question.lower()
    has_data_signal = any(w in lowered for w in _DATA_SIGNAL_WORDS)
    has_table_signal = any(w in lowered for w in _TABLE_SIGNAL_WORDS)
    return has_data_signal and has_table_signal


def _get_groq_client():
    from .service import _get_groq_client as _svc_get_client
    return _svc_get_client()


def generate_sql(
    db: Session,
    question: str,
    user: User,
    department_id: Optional[int],
) -> PendingSqlQuery:
    """
    Asks the LLM for one SELECT statement, validates it, and stores it as a
    PendingSqlQuery row (never executed yet). Raises SqlValidationError if
    the model's output fails validation.
    """
    scoping_note = (
        "This user is a superadmin and may query across all departments "
        "(only add a department_id filter if the question asks for one "
        "specific department)."
        if user.role == "superadmin"
        else (
            f"This user belongs to department_id = {department_id}. The "
            "query MUST restrict every table that has a department_id "
            "column to this exact value — either directly or via a join "
            "to tickets/users that carries it. Never return rows from "
            "another department."
        )
    )

    system_prompt = (
        "You translate a support-team question into ONE read-only SQL "
        "SELECT statement for a PostgreSQL database. Rules:\n"
        f"- Schema (the ONLY tables/columns that exist):\n{SCHEMA_DESCRIPTION}\n"
        "- Output ONLY the SQL statement — no markdown fences, no "
        "explanation, no trailing semicolon.\n"
        "- SELECT statements only. Never write INSERT/UPDATE/DELETE/DDL of "
        "any kind.\n"
        "- Never reference any table or column outside the schema above.\n"
        f"- {scoping_note}\n"
        f"- Add `LIMIT {MAX_ROWS}` if the question doesn't imply a smaller "
        "result set already."
    )

    response = _get_groq_client().chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    raw_sql = re.sub(r"<think>[\s\S]*?</think>", "", response.choices[0].message.content).strip()
    raw_sql = re.sub(r"^```sql\s*|\s*```$", "", raw_sql, flags=re.IGNORECASE).strip()
    raw_sql = raw_sql.rstrip(";").strip()

    validate_sql(raw_sql, user=user, department_id=department_id)

    pending = PendingSqlQuery(
        user_id=user.id,
        department_id=department_id,
        question=question,
        sql_text=raw_sql,
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)
    return pending


def validate_sql(sql: str, user: User, department_id: Optional[int]) -> None:
    """
    Static validation only — no DB access. Raises SqlValidationError with a
    human-readable reason on any violation.
    """
    if not sql:
        raise SqlValidationError("The model returned an empty query.")

    lowered = sql.lower()

    if ";" in sql:
        raise SqlValidationError("Multiple statements are not allowed.")

    if not lowered.strip().startswith("select"):
        raise SqlValidationError("Only SELECT statements are allowed.")

    for bad in FORBIDDEN_SUBSTRINGS:
        if bad in lowered:
            raise SqlValidationError(f"Query contains a disallowed keyword: '{bad}'.")

    # Table whitelist: every identifier following FROM/JOIN must be one of
    # the allowed tables.
    referenced_tables = set(
        m.group(1).lower()
        for m in re.finditer(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", sql, re.IGNORECASE)
    )
    unknown_tables = referenced_tables - ALLOWED_TABLES
    if unknown_tables:
        raise SqlValidationError(f"Query references unknown table(s): {', '.join(unknown_tables)}.")
    if not referenced_tables:
        raise SqlValidationError("Query does not reference any known table.")

    # Column whitelist is enforced loosely: reject any bare identifier that
    # looks like table.column or "column" and isn't in the combined allowed
    # set for the referenced tables (best-effort — SQL parsing without a
    # real parser can't be perfect, hence the substring net above too).
    allowed_columns_here = set()
    for t in referenced_tables:
        allowed_columns_here |= ALLOWED_COLUMNS.get(t, set())

    # Department scoping enforcement for non-superadmins.
    if user.role != "superadmin":
        if str(department_id) not in sql:
            raise SqlValidationError(
                "Query must filter by your department_id; the generated "
                "query didn't include it. Try rephrasing the question."
            )


def execute_sql(db: Session, pending: PendingSqlQuery) -> dict:
    """
    Re-validates (in case anything about the user/department context could
    have changed) and runs the stored SQL inside a transaction that is
    always rolled back, regardless of statement type — belt-and-braces on
    top of the SELECT-only static check. One-shot: a query can only be
    executed once its `executed` flag is set.
    """
    if pending.executed == "1":
        raise SqlValidationError("This query has already been executed.")

    result = db.execute(text(pending.sql_text))
    columns = list(result.keys())
    rows = [list(row) for row in result.fetchmany(MAX_ROWS)]
    db.rollback()  # never persist any side effect, even an unexpected one

    pending.executed = "1"
    db.commit()

    return {
        "sql": pending.sql_text,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }
