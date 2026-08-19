"""CommercialBillingSettings model - Seller business details, taxes, invoice numbering sequence, and templates"""

from typing import Optional, List
from datetime import datetime
from beanie import Document
from pydantic import BaseModel, Field


class TaxRateConfig(BaseModel):
    name: str  # e.g. "VAT 19.25%"
    rate: float  # e.g. 19.25
    is_inclusive: bool = False
    is_active: bool = True


class CommercialBillingSettings(Document):
    company_name: str = "STOCKFLOW Technologies"
    subtitle: str = "Inventory & Retail Management Systems"
    logo_url: Optional[str] = None
    address: Optional[str] = "Douala, Cameroon"
    phone: Optional[str] = "+237 600 000 000"
    email: Optional[str] = "billing@stockflow.com"
    website: Optional[str] = "https://stockflow.app"
    tax_id: Optional[str] = "M082612345678"

    bank_name: Optional[str] = "UBA Bank"
    bank_account_number: Optional[str] = "10023-000456-99"
    bank_swift_code: Optional[str] = "UNAFCMCX"
    payment_instructions: Optional[str] = "Please make payments via bank transfer or Mobile Money (MTN/Orange) citing the Invoice Number as reference."

    invoice_prefix: str = "INV-"
    invoice_next_number: int = 1001

    contract_prefix: str = "MNT-"
    contract_next_number: int = 1001

    default_currency: str = "XAF"
    default_payment_terms_days: int = 14
    default_terms_conditions: str = "1. Payments are due within the specified terms.\n2. Monthly maintenance starts upon deployment and is billed monthly.\n3. Overdue invoices past the grace period may result in service suspension."

    taxes: List[TaxRateConfig] = Field(default_factory=lambda: [
        TaxRateConfig(name="VAT 19.25%", rate=19.25, is_inclusive=False, is_active=True),
        TaxRateConfig(name="Zero Tax (0%)", rate=0.0, is_inclusive=False, is_active=True)
    ])

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "commercial_billing_settings"
