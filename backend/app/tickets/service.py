# This file holds the business logic for customer support tickets.
# It coordinates ticket visibility, lifecycle decisions, and support workflow behavior.

import secrets
import string

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.departments.models import Department
from app.shared.constants import UserRole
from app.tickets.models import Ticket
from app.tickets.schemas import TicketCreate


TICKET_ID_ALPHABET = string.ascii_uppercase + string.digits
TICKET_ID_LENGTH = 6


def list_tickets(db: Session, current_user: User) -> list[Ticket]:
    query = db.query(Ticket)

    if current_user.role == UserRole.SUPERADMIN.value:
        return query.order_by(Ticket.created_at.desc()).all()

    if current_user.role == UserRole.ADMIN.value:
        if current_user.department_id is None:
            return []
        return (
            query.filter(Ticket.department_id == current_user.department_id)
            .order_by(Ticket.created_at.desc())
            .all()
        )

    if current_user.role == UserRole.AGENT.value:
        return (
            query.filter(Ticket.assigned_to == current_user.id)
            .order_by(Ticket.created_at.desc())
            .all()
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to view tickets",
    )


def get_ticket(ticket_id: str, db: Session, current_user: User) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None or not _can_access_ticket(ticket, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return ticket


def create_ticket(data: TicketCreate, db: Session, current_user: User) -> Ticket:
    if current_user.role == UserRole.ADMIN.value:
        if current_user.department_id != data.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins can only create tickets for their department",
            )
    elif current_user.role != UserRole.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create tickets",
        )

    assigned_user = db.get(User, data.assigned_to)
    if assigned_user is None or assigned_user.role != UserRole.AGENT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='assigned_to must reference a user with role="agent"',
        )

    department = db.get(Department, data.department_id)
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="department_id must reference an existing department",
        )

    if assigned_user.department_id != data.department_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="assigned_to agent must belong to the ticket department",
        )

    ticket = Ticket(id=_generate_ticket_id(db), **data.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def resolve_ticket(
    ticket_id: str,
    db: Session,
    current_user: User,
) -> Ticket:
    ticket = get_ticket(ticket_id, db, current_user)
    ticket.status = TicketStatus.RESOLVED.value
    db.commit()
    db.refresh(ticket)
    return ticket


def _can_access_ticket(ticket: Ticket, current_user: User) -> bool:
    if current_user.role == UserRole.SUPERADMIN.value:
        return True
    if current_user.role == UserRole.ADMIN.value:
        return ticket.department_id == current_user.department_id
    if current_user.role == UserRole.AGENT.value:
        return ticket.assigned_to == current_user.id
    return False


def _generate_ticket_id(db: Session) -> str:
    while True:
        ticket_id = "".join(
            secrets.choice(TICKET_ID_ALPHABET) for _ in range(TICKET_ID_LENGTH)
        )
        if db.get(Ticket, ticket_id) is None:
            return ticket_id
