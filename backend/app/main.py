from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Wasla")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers will be registered here as each module is implemented.
# app.include_router(auth_router, prefix="/auth", tags=["auth"])
# app.include_router(departments_router, prefix="/departments", tags=["departments"])
# app.include_router(tickets_router, prefix="/tickets", tags=["tickets"])
# app.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])
# app.include_router(telephony_router, prefix="/telephony", tags=["telephony"])
