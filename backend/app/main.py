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
from app.shared.database import Base, engine
from app.users.router import router as users_router
from app.chatbot import models as chatbot_models
from app.chatbot.router import router as chatbot_router


app = FastAPI(title="Wasla")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3003",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
