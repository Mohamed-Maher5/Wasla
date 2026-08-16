from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.telephony.router import router as telephony_router


app = FastAPI(title="Wasla")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers will be registered here as each module is implemented.
app.include_router(auth_router)
app.include_router(telephony_router)
# app.include_router(departments_router, prefix="/departments", tags=["departments"])
# app.include_router(tickets_router, prefix="/tickets", tags=["tickets"])
# app.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])
