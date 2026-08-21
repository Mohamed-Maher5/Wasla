# Wasla (وَصْلَة)

Wasla is an internal support platform for companies with multiple departments (HR, Finance, etc.). Superadmins, department admins, and agents manage support tickets through role-based access with **strict department-level data isolation**.

Two AI features are built in:

- **Outbound calling agent** — phones customers in Egyptian Arabic (Vonage/Twilio + ElevenLabs) to confirm whether their reported issue is resolved.
- **RAG chatbot (مساعد وَصْلَة)** — answers questions using **only** the documents uploaded to the user's own department (Groq LLM + pgvector embeddings).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python · FastAPI · SQLAlchemy |
| Database | PostgreSQL + `pgvector` (Docker) |
| Frontend | React 19 · Vite |
| LLM | Groq API |
| Embeddings | HuggingFace (`sentence-transformers`, 384-dim) |
| Telephony | Vonage / Twilio · ElevenLabs TTS |

| Service | Port |
|---|---|
| Backend (FastAPI / uvicorn) | `8000` |
| Frontend (Vite dev server) | `3003` (pinned in `vite.config.js`) |
| PostgreSQL | `5433` → container's `5432` |

---

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker + Docker Compose
- Node.js 18+

---

## Getting Started

### 1. Create env + install everything

```bash
uv venv
source .venv/bin/activate
uv pip install -r backend/requirements.txt
```

> The backend reads its configuration from a root `.env` file.
> Copy the template and fill in at least `DATABASE_URL` and `JWT_SECRET`
> (the chatbot needs `GROQ_LLM_API_KEY` + `HUGGINGFACE_API_KEY`; telephony keys are optional):

```bash
cp .env.example .env
```

### 2. Start Postgres + enable pgvector

```bash
docker compose up -d
docker exec -it wasla-db psql -U wasla -d wasla -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3. Run backend (creates tables), then seed superadmin

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --app-dir backend
```

In a second terminal, create the first superadmin:

```bash
PYTHONPATH=backend python3 << 'EOF'
from app.shared.database import SessionLocal
from app.auth.models import User
from app.auth.service import hash_password

db = SessionLocal()
existing = db.query(User).filter((User.id == 1) | (User.email == "superadmin@wasla.com")).first()
if existing:
    print("Already exists:", existing.id, existing.email, existing.role)
else:
    user = User(id=1, name="superadmin", email="superadmin@wasla.com",
        password_hash=hash_password("1234"), role="superadmin", department_id=None)
    db.add(user)
    db.commit()
    print("Created superadmin:", user.id, user.email, user.role)
db.close()
EOF
```

> Swagger API docs: <http://127.0.0.1:8000/docs>

### 4. Frontend

```bash
cd frontend
npm install
echo "VITE_API_BASE_URL=http://127.0.0.1:8000" > .env
npm run dev
```

Open **<http://localhost:3003>** and log in.

---

## Roles & What Each One Can Do

| Role | Capabilities |
|---|---|
| **Superadmin** (`superadmin@wasla.com` / `1234`) | Create departments · create admins · view platform-wide stats |
| **Admin** | Created by the superadmin, bound to one department · create agents · create tickets · upload department documents · chat with مساعد وَصْلَة over that department's knowledge base |
| **Agent** | Created by an admin · see assigned tickets · resolve/unresolve · call customers · chat with مساعد وَصْلَة |

All chat history, document search, and ticket data are isolated per department — a user can never see another department's data.

---

## Resetting Data

To wipe all operational rows while keeping the superadmin account:

```bash
docker exec -it wasla-db psql -U wasla -d wasla -c "
DELETE FROM call_attempts;
DELETE FROM chat_logs;
DELETE FROM conversations;
DELETE FROM document_chunks;
DELETE FROM documents;
DELETE FROM knowledge_documents;
DELETE FROM tickets;
DELETE FROM users WHERE email != 'superadmin@wasla.com';
DELETE FROM departments;
"
```

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, router registration
│   │   ├── auth/                # login, JWT, role enforcement
│   │   ├── users/               # user creation (admins & agents)
│   │   ├── departments/         # department management
│   │   ├── tickets/             # ticket lifecycle
│   │   ├── documents/           # legacy documents module (superseded by chatbot)
│   │   ├── telephony/           # outbound calling agent (scripts, TTS, status)
│   │   ├── chatbot/             # RAG chatbot: uploads, embeddings, Q&A, history
│   │   └── shared/              # config (.env), database session, constants
│   └── scripts/                 # helper scripts (seed users, create tables)
├── frontend/
│   ├── src/
│   │   ├── api.js               # single bridge to the backend REST API
│   │   ├── pages/               # Login, Superadmin/Admin/Agent dashboards, Documents
│   │   └── components/          # ChatPanel (chat + history), TicketCard, CallButton
│   └── vite.config.js           # port 3003 (strict)
├── docker-compose.yml           # wasla-db (pgvector) on port 5433
└── .env.example                 # backend environment template
```

---

## Useful Notes

- **CORS**: the backend only accepts requests from `http://localhost:3003` (configured in `backend/app/main.py`).
- **Department isolation is enforced server-side**: admins/agents always operate on their own department; client-sent department IDs are ignored except for superadmins.
- Tables are created automatically on backend startup (`Base.metadata.create_all`).
- The frontend pins port `3003` with `strictPort: true` — if the port is busy, Vite will fail instead of silently switching ports.
