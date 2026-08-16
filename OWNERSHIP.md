# Wasla -- Folder Ownership

Three people, three non-overlapping areas. GitHub will automatically ask
the right person for review on any PR -- see `.github/CODEOWNERS`.

**Golden rule:** never edit a file outside your own area below. If you need
something from another area, ask for a function to call -- don't edit their
file directly.

## You -- foundation, auth, telephony, wiring

    backend/app/shared/       config, database connection, shared constants
    backend/app/auth/         login, JWT, get_current_user(), require_role()
    backend/app/telephony/    Twilio webhooks, the AI call script, call outcomes
    backend/app/main.py       wires every module's router into one app
    frontend/src/api.js       the contract -- one function per backend endpoint

## Person A -- departments + tickets + the whole frontend

    backend/app/departments/  create/list departments (superadmin only)
    backend/app/tickets/      create/list/resolve tickets, role-based filtering
    frontend/src/App.jsx      routing + login state
    frontend/src/pages/       Login, TicketList, TicketDetail, Documents
    frontend/src/components/  TicketCard, ChatPanel, CallButton, ResolveButtons

## Person B -- chatbot

    backend/app/chatbot/      document upload, chunking, embeddings, Q&A with citations

## The two functions that connect everyone

These are the only places work crosses a boundary -- agree on their exact
shape before building, then don't change them without a heads-up:

- `auth.service.get_current_user()` and `auth.service.require_role()` --
  everyone reads from these, only You edit them
- `tickets.service.set_status(ticket_id, status)` -- telephony calls this
  when an AI call confirms an outcome; Person A owns and exposes it

## Before writing any code

1. Copy `.env.example` to `.env` (already fixed -- Postgres runs on port
   5433 via docker-compose, not the default 5432)
2. `docker compose up -d`
3. Agree the exact API endpoint list together, once, before splitting up
