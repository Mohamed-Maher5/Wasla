-- Run as a PostgreSQL administrator after creating a dedicated LOGIN role.
-- The application must connect for generated SQL as wasla_nl2sql_reader,
-- NEVER as the database owner. Provision a strong password outside source control.
-- Example (run separately): CREATE ROLE wasla_nl2sql_reader LOGIN PASSWORD '<secret>';
-- IMPORTANT: the application DB owner must not use this URL.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM wasla_nl2sql_reader;
GRANT USAGE ON SCHEMA public TO wasla_nl2sql_reader;
GRANT SELECT (id, name) ON TABLE public.departments TO wasla_nl2sql_reader;
GRANT SELECT (id, name, email, role, department_id, created_by)
  ON TABLE public.users TO wasla_nl2sql_reader;
GRANT SELECT (id, client_name, client_phone_number, description, status,
  assigned_to, created_by, department_id, created_at)
  ON TABLE public.tickets TO wasla_nl2sql_reader;
ALTER TABLE public.departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tickets ENABLE ROW LEVEL SECURITY;
-- FORCE also restricts owner connections; review app behavior before enabling.
DROP POLICY IF EXISTS nl2sql_dept_read ON public.departments;
CREATE POLICY nl2sql_dept_read ON public.departments FOR SELECT
 TO wasla_nl2sql_reader
 USING (id = nullif(current_setting('wasla.department_id', true), '')::integer);
DROP POLICY IF EXISTS nl2sql_users_read ON public.users;
CREATE POLICY nl2sql_users_read ON public.users FOR SELECT
 TO wasla_nl2sql_reader
 USING (department_id = nullif(current_setting('wasla.department_id', true), '')::integer);
DROP POLICY IF EXISTS nl2sql_tickets_read ON public.tickets;
CREATE POLICY nl2sql_tickets_read ON public.tickets FOR SELECT
 TO wasla_nl2sql_reader
 USING (department_id = nullif(current_setting('wasla.department_id', true), '')::integer);
-- Verify reader is NOT superuser, NO BYPASSRLS, and is NOT a table owner.
-- Validate policies and grants with two departments before enabling in production.
