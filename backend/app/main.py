from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import models as auth_models
from app.auth.router import router as auth_router
from app.departments import models as department_models
from app.departments.router import router as departments_router
from app.documents import models as document_models
from app.documents.router import router as documents_router
from app.telephony.router import router as telephony_router
from app.tickets import models as ticket_models
from app.tickets.router import router as tickets_router
from app.shared.config import settings
from app.shared.database import Base, engine
from app.users.router import router as users_router
from app.chatbot import models as chatbot_models
from app.chatbot.router import router as chatbot_router


app = FastAPI(title="Wasla")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3003",
        "http://127.0.0.1:3003",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    services = {}

    # Vonage — check config
    services["vonage"] = {
        "configured": bool(settings.vonage_application_id and settings.vonage_private_key_path and settings.vonage_from_number),
        "error": None,
    }
    if not services["vonage"]["configured"]:
        missing = []
        if not settings.vonage_application_id:
            missing.append("VONAGE_APPLICATION_ID")
        if not settings.vonage_private_key_path:
            missing.append("VONAGE_PRIVATE_KEY_PATH")
        if not settings.vonage_from_number:
            missing.append("VONAGE_FROM_NUMBER")
        services["vonage"]["error"] = f"Missing: {', '.join(missing)}"

    # Groq — check key + ping
    services["groq"] = {"configured": bool(settings.groq_llm_api_key), "error": None}
    if not settings.groq_llm_api_key:
        services["groq"]["error"] = "Missing: GROQ_LLM_API_KEY"
    else:
        try:
            import requests as _r
            resp = _r.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.groq_llm_api_key}"},
                timeout=5,
            )
            if resp.status_code != 200:
                services["groq"]["error"] = f"API returned {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            services["groq"]["error"] = f"Connection failed: {e}"

    # ElevenLabs — check key + ping
    services["elevenlabs"] = {"configured": bool(settings.elevenlabs_api_key), "error": None}
    if not settings.elevenlabs_api_key:
        services["elevenlabs"]["error"] = "Missing: ELEVENLABS_API_KEY"
    else:
        try:
            import requests as _r
            resp = _r.get(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": settings.elevenlabs_api_key},
                timeout=5,
            )
            if resp.status_code != 200:
                services["elevenlabs"]["error"] = f"API returned {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            services["elevenlabs"]["error"] = f"Connection failed: {e}"

    # HuggingFace — check key
    services["huggingface"] = {"configured": bool(settings.huggingface_api_key), "error": None}
    if not settings.huggingface_api_key:
        services["huggingface"]["error"] = "Missing: HUGGINGFACE_API_KEY"

    # Public URL — check
    services["public_url"] = {"configured": bool(settings.public_base_url), "error": None}
    if not settings.public_url if hasattr(settings, "public_url") else not getattr(settings, "public_base_url", ""):
        services["public_url"]["error"] = "Missing: PUBLIC_BASE_URL (needed for Vonage webhooks)"

    all_ok = all(s["configured"] and not s["error"] for s in services.values())

    return {"status": "healthy" if all_ok else "degraded", "services": services}


@app.on_event("startup")
def create_database_tables() -> None:
    # Keep model imports above this call so SQLAlchemy has all table metadata.
    _ = (auth_models, department_models, ticket_models, document_models, chatbot_models)
    Base.metadata.create_all(bind=engine)


app.include_router(auth_router)
app.include_router(telephony_router)
app.include_router(departments_router)
app.include_router(documents_router)
app.include_router(tickets_router)
app.include_router(users_router)
app.include_router(chatbot_router)
