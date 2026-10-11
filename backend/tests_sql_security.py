"""Focused NL2SQL validation checks (run from backend after installing requirements)."""
from types import SimpleNamespace
import pytest
from app.chatbot.nl2sql import validate_sql, SqlValidationError

user = SimpleNamespace(id=1, role="agent", department_id=7)

@pytest.mark.parametrize("sql", [
    "SELECT * FROM tickets",
    "SELECT id FROM tickets WHERE department_id=7 UNION SELECT id FROM tickets",
    "SELECT id FROM tickets WHERE department_id=7; SELECT id FROM users",
    "SELECT password_hash FROM users",
    "SELECT pg_sleep(10) FROM tickets",
    "SELECT set_config('wasla.department_id', '8', true) FROM tickets",
    "SELECT id FROM tickets WHERE id IN (SELECT id FROM tickets)",
    "SELECT id FROM tickets LIMIT 1000000",
])
def test_rejects_unsafe_sql(sql):
    with pytest.raises(SqlValidationError):
        validate_sql(sql, user=user, department_id=7)

@pytest.mark.parametrize("sql", [
    "SELECT COUNT(*) FROM tickets WHERE department_id = 7",
    "SELECT status, COUNT(*) FROM tickets WHERE department_id = 7 GROUP BY status LIMIT 20",
    "SELECT id, name FROM departments WHERE id = 7",
])
def test_accepts_safe_sql_shapes(sql):
    validate_sql(sql, user=user, department_id=7)


def test_requires_selected_department():
    with pytest.raises(SqlValidationError):
        validate_sql("SELECT COUNT(*) FROM tickets", user=user, department_id=None)
