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
from functools import lru_cache
from typing import Optional

from sqlalchemy import create_engine, text
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
  - id (text, primary key)
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
    # Existence questions, e.g. "هل في تذاكر تم إنجازها؟"
    "هل في", "هل يوجد", "هل هناك", "هل عندك", "هل لديك", "عندك أي",
    "لديك أي", "فيه أي", "يوجد أي",
    # English
    "how many", "count", "list", "show me", "average", "total", "statistics",
    "is there", "are there", "any tickets", "any users",
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
        max_tokens=500,
        reasoning_effort="none",
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
    """Fail-closed AST validation; database RLS remains the enforcement boundary."""
    if not isinstance(sql, str) or not sql.strip() or len(sql) > 5000:
        raise SqlValidationError("Invalid SQL query")
    if department_id is None:
        raise SqlValidationError("Select a department before querying structured data")

    from sqlglot import parse, exp
    try:
        statements = parse(sql, read="postgres")
    except Exception as exc:
        raise SqlValidationError("Could not parse SQL") from exc
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise SqlValidationError("Exactly one SELECT is required")
    tree = statements[0]
    # Restrict query shape. No CTEs, subqueries, set operations, user-defined
    # functions, or session-setting expressions. The dedicated DB login + RLS
    # are responsible for department scoping, not text matching.
    forbidden_types = (
        exp.Subquery, exp.With, exp.Union, exp.Except, exp.Intersect,
        exp.Command, exp.Insert, exp.Update, exp.Delete, exp.Create,
        exp.Drop, exp.Alter, exp.Window,
    )
    if any(isinstance(node, forbidden_types) for node in tree.walk()):
        raise SqlValidationError("Unsupported SQL construct")
    tables = list(tree.find_all(exp.Table))
    if not tables or any(t.name.lower() not in ALLOWED_TABLES or t.db or t.catalog for t in tables):
        raise SqlValidationError("Query references a disallowed table")
    for node in tree.walk():
        if isinstance(node, exp.Star) and not isinstance(node.parent, exp.Count):
            raise SqlValidationError("SELECT * is disallowed")
        if isinstance(node, exp.Select) and node is not tree:
            raise SqlValidationError("Nested SELECT is disallowed")
        if isinstance(node, exp.Func) and not isinstance(
            node, (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max)
        ):
            raise SqlValidationError("SQL functions other than basic aggregates are disallowed")
        if isinstance(node, exp.Column) and node.name.lower() not in (
            set().union(*(ALLOWED_COLUMNS[t.name.lower()] for t in tables))
        ):
            raise SqlValidationError("Query references a disallowed column")
    # A full-database result isn't useful in chat; cap execution even if
    # LIMIT is absent. Database permissions further restrict returned columns.
    if tree.args.get("limit"):
        limit = tree.args["limit"].expression
        if not isinstance(limit, exp.Literal) or not limit.is_int or int(limit.this) > MAX_ROWS:
            raise SqlValidationError(f"LIMIT must be an integer <= {MAX_ROWS}")


@lru_cache(maxsize=1)
def _reader_engine():
    url = settings.NL2SQL_READONLY_DATABASE_URL
    if not url:
        raise SqlValidationError(
            "NL2SQL is unavailable until a restricted PostgreSQL reader is configured"
        )
    return create_engine(url, pool_pre_ping=True)


def execute_sql(db: Session, pending: PendingSqlQuery) -> dict:
    """Return SQL results immediately, using a separate RLS-protected DB login."""
    if pending.executed == "1":
        raise SqlValidationError("This query has already been executed")
    if pending.department_id is None:
        raise SqlValidationError("A department must be selected")
    # Never run generated SQL using the application's unrestricted Session.
    engine = _reader_engine()
    # PostgreSQL SET LOCAL settings only live until the transaction ends.
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text("SET LOCAL statement_timeout = '3000ms'"))
            conn.execute(text("SET LOCAL row_security = on"))
            conn.execute(
                text("SELECT set_config('wasla.department_id', :dept, true)"),
                {"dept": str(pending.department_id)},
            )
            result = conn.execute(text(pending.sql_text))
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchmany(MAX_ROWS)]
        finally:
            transaction.rollback()
    pending.executed = "1"
    db.commit()
    return {"sql": pending.sql_text, "columns": columns,
            "rows": rows, "row_count": len(rows)}
