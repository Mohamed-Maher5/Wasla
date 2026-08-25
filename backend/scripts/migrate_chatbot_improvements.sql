-- Migration: RAG chatbot improvements (web-search fallback, personas, NL->SQL, voice)
-- Run this once against your existing Wasla database. Safe to re-run —
-- every statement is guarded with IF NOT EXISTS.

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS persona VARCHAR(30) NOT NULL DEFAULT 'general';

ALTER TABLE chat_logs
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) NOT NULL DEFAULT 'document';

ALTER TABLE chat_logs
    ADD COLUMN IF NOT EXISTS web_sources TEXT;

CREATE TABLE IF NOT EXISTS pending_sql_queries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    department_id INTEGER REFERENCES departments(id),
    question TEXT NOT NULL,
    sql_text TEXT NOT NULL,
    executed VARCHAR(1) NOT NULL DEFAULT '0',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_pending_sql_queries_user_id ON pending_sql_queries(user_id);
