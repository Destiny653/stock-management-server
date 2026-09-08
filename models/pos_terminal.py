"""POSTerminal model – Registers POS terminals operating against a parent Store location."""
from typing import Annotated, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from beanie import Document, Indexed
from pydantic import Field


class POSTerminalStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    CLOSED = "closed"


class POSTerminal(Document):
    organization_id: Annotated[str, Indexed()]
    store_id: Annotated[str, Indexed()]  # Must reference a Location of type STORE or BRANCH
    store_name: Optional[str] = None
    name: Annotated[str, Indexed()]  # e.g., "Terminal 01 - Checkout Desk A"
    code: Annotated[str, Indexed()]  # e.g., "POS-DLA-01"
    status: POSTerminalStatus = POSTerminalStatus.ACTIVE
    assigned_cashier_id: Optional[str] = None
    assigned_cashier_name: Optional[str] = None
    
    # Active register session state
    current_session: Optional[Dict[str, Any]] = None  # { session_id, cashier_id, opened_at, opening_cash, total_sales }
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "pos_terminals"
