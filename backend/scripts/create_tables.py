from app.shared.database import Base, engine, ensure_pgvector_extension
from app.auth.models import User
from app.departments.models import Department
from app.tickets.models import Ticket
from app.telephony.models import CallAttempt
from app.chatbot.models import KnowledgeDocument, DocumentChunk, ChatLog

ensure_pgvector_extension(engine)
Base.metadata.create_all(bind=engine)
print("Tables created successfully")
