# This file defines shared vocabulary used across the Wasla backend.
# It keeps role and ticket state names consistent between independent modules.

from enum import Enum


class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    AGENT = "agent"


class TicketStatus(str, Enum):
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
