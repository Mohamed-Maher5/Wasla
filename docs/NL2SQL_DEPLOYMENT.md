# NL2SQL deployment safeguards

The chat executes structured SQL questions **immediately**, without asking the user to approve an SQL statement. It is **disabled by default** until a restricted reader is configured. This does not change the existing role/permission API.

1. Provision PostgreSQL `wasla_nl2sql_reader` as a login with a secret password (never check credentials into Git). The role must not own the application tables, be superuser, inherit broad privileges, or have `BYPASSRLS`.
2. Review and apply `backend/scripts/setup_nl2sql_reader.sql` as DB administrator. These example policies protect `users`, `tickets`, and `departments`; validate existing policy interactions and PostgreSQL PUBLIC grants, and ensure the reader has no other unintended privileges.
3. Set `NL2SQL_READONLY_DATABASE_URL` privately in backend `.env`, pointing at **that reader**. Do not use the app's `DATABASE_URL`.
4. Confirm a user in department A cannot return rows from department B, including via joins, unions, functions, set configuration calls, and crafted identifiers. Confirm timeouts and that no write occurs.
5. Confirm the superadmin explicitly selects a department for SQL queries. Cross-department SQL is deliberately unavailable.
6. Review the approved column list; client names, contact information and employee emails are confidential. Narrow it further for your organization's policy.

The query parser is an additional guard, not a substitute for row-level security. The service fails closed if a restricted reader is not configured. External LLM prompts may include schema information and the user's query: assess data-handling requirements before enabling.

## Smoke tests

From the backend directory after installing requirements and `pytest`:

```bash
python -m pytest tests_sql_security.py -q
```

These are parser tests only. An end-to-end RLS integration test using a real
PostgreSQL instance and separate department fixtures is still required before
turning the feature on for production users.
