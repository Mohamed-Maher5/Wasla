# This file exposes ticket endpoints for the Wasla backend.
# It is the HTTP boundary for customer support ticket workflows.

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import get_current_user, require_role
from app.shared.database import get_db
from app.tickets.schemas import TicketCreate, TicketOut
from app.tickets.service import (
    create_ticket,
    get_ticket,
    list_tickets,
    resolve_ticket,
)


router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("", response_model=list[TicketOut])
def get_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TicketOut]:
    return list_tickets(db, current_user)


@router.post("", response_model=TicketOut)
def post_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin")),
) -> TicketOut:
    return create_ticket(data, db, current_user)


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket_by_id(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TicketOut:
    return get_ticket(ticket_id, db, current_user)


@router.post("/{ticket_id}/resolve", response_model=TicketOut)
def post_ticket_resolve(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TicketOut:
    return resolve_ticket(ticket_id, db, current_user)
