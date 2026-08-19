"""CommercialInvoice model - Invoice entity with itemized line items, tax, discounts, and payments"""

from typing import Annotated, Optional, List
from datetime import datetime
from beanie import Document, Indexed
from pydantic import BaseModel, Field
from enum import Enum


class CommercialInvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    VOID = "void"


class CommercialPaymentStatus(str, Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"


class InvoiceBillingType(str, Enum):
    ONE_TIME = "ONE_TIME"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"
    RECURRING = "RECURRING"


class CommercialInvoiceItem(BaseModel):
    description: str
    product_service_id: Optional[str] = None
    product_service_code: Optional[str] = None
    billing_type: InvoiceBillingType = InvoiceBillingType.ONE_TIME
    quantity: float = 1.0
    unit_price: float = 0.0
    discount: float = 0.0
    tax_rate: float = 0.0  # Percentage e.g. 19.25
    tax_amount: float = 0.0
    total: float = 0.0


class CommercialInvoice(Document):
    invoice_number: Annotated[str, Indexed(unique=True)]  # e.g. INV-2026-0001
    organization_id: Annotated[str, Indexed()]
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    billing_address: Optional[str] = None

    invoice_date: datetime = Field(default_factory=datetime.utcnow)
    due_date: datetime
    currency: str = "XAF"

    contract_id: Optional[str] = None  # Linked maintenance contract if recurring

    items: List[CommercialInvoiceItem] = Field(default_factory=list)

    subtotal: float = 0.0
    total_discount: float = 0.0
    total_tax: float = 0.0
    total_amount: float = 0.0
    amount_paid: float = 0.0
    balance_due: float = 0.0

    payment_status: CommercialPaymentStatus = CommercialPaymentStatus.UNPAID
    status: CommercialInvoiceStatus = CommercialInvoiceStatus.SENT

    notes: Optional[str] = None
    terms_conditions: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "commercial_invoices"
