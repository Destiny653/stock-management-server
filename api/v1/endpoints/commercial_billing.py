"""Commercial Billing endpoints for software sales, recurring maintenance, invoicing, and MRR analytics"""

from typing import List, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from beanie import PydanticObjectId

from api import deps
from models.user import User
from models.organization import Organization
from models.service_product import ServiceProduct, CommercialBillingType, ServiceProductCategory
from models.maintenance_contract import MaintenanceContract, ContractStatus, ContractBillingFrequency, ServiceStatus
from models.commercial_invoice import CommercialInvoice, CommercialInvoiceStatus, CommercialPaymentStatus, CommercialInvoiceItem, InvoiceBillingType
from models.commercial_payment import CommercialPayment, CommercialPaymentMethod
from models.commercial_billing_settings import CommercialBillingSettings, TaxRateConfig
from models.alert import Alert, AlertType, AlertPriority
from models.audit_log import AuditLog

router = APIRouter()


# ─── Seed Helper ──────────────────────────────────────────────────────────────
async def get_or_create_settings() -> CommercialBillingSettings:
    settings_doc = await CommercialBillingSettings.find_one({})
    if not settings_doc:
        settings_doc = CommercialBillingSettings()
        await settings_doc.create()
    return settings_doc


# ─── Catalogue Endpoints ──────────────────────────────────────────────────────
@router.get("/catalogue")
async def get_catalogue(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """List commercial service & product catalogue items. Seeds defaults if empty."""
    items = await ServiceProduct.find_all().to_list()
    if not items:
        default_items = [
            ServiceProduct(
                name="STOCKFLOW Standard Edition",
                code="SF-STD",
                category=ServiceProductCategory.SOFTWARE,
                description="Core inventory & POS license for small businesses",
                price=500000.0,
                billing_type=CommercialBillingType.ONE_TIME,
            ),
            ServiceProduct(
                name="STOCKFLOW Professional Edition",
                code="SF-PRO",
                category=ServiceProductCategory.SOFTWARE,
                description="Full inventory, multi-store, & vendor management license",
                price=1000000.0,
                billing_type=CommercialBillingType.ONE_TIME,
            ),
            ServiceProduct(
                name="STOCKFLOW Enterprise Edition",
                code="SF-ENT",
                category=ServiceProductCategory.SOFTWARE,
                description="Enterprise license with unlimited stores & API access",
                price=1500000.0,
                billing_type=CommercialBillingType.ONE_TIME,
            ),
            ServiceProduct(
                name="System Implementation & Staff Training",
                code="SF-IMP",
                category=ServiceProductCategory.ONE_TIME_SERVICE,
                description="Onsite configuration, data migration & staff training",
                price=300000.0,
                billing_type=CommercialBillingType.ONE_TIME,
            ),
            ServiceProduct(
                name="Additional POS Terminal Installation",
                code="SF-POS-ADD",
                category=ServiceProductCategory.ONE_TIME_SERVICE,
                description="Setup & hardware integration for additional POS register",
                price=100000.0,
                billing_type=CommercialBillingType.ONE_TIME,
            ),
            ServiceProduct(
                name="Monthly Maintenance & Technical Support",
                code="SF-MNT-MON",
                category=ServiceProductCategory.RECURRING_SERVICE,
                description="Monthly bug fixes, security updates, backups & technical support",
                price=100000.0,
                billing_type=CommercialBillingType.RECURRING,
            ),
            ServiceProduct(
                name="Cloud Hosting & Data Backup Subscription",
                code="SF-HOST-MON",
                category=ServiceProductCategory.RECURRING_SERVICE,
                description="Dedicated cloud infrastructure & daily automated backups",
                price=35000.0,
                billing_type=CommercialBillingType.RECURRING,
            ),
        ]
        for item in default_items:
            await item.create()
        items = await ServiceProduct.find_all().to_list()
    return items


@router.post("/catalogue")
async def create_catalogue_item(
    item_in: dict,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Create a new service/product offering in commercial catalogue."""
    item = ServiceProduct(**item_in)
    await item.create()

    await AuditLog(
        organization_id=getattr(current_user, "organization_id", "platform") or "platform",
        user_id=str(current_user.id),
        user_name=current_user.full_name or current_user.username,
        action="CREATE_COMMERCIAL_SERVICE",
        resource_type="ServiceProduct",
        resource_id=str(item.id),
        details={"name": item.name, "price": item.price, "billing_type": item.billing_type},
    ).create()

    return item


@router.put("/catalogue/{item_id}")
async def update_catalogue_item(
    item_id: str,
    item_in: dict,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Update catalogue item."""
    item = await ServiceProduct.get(PydanticObjectId(item_id))
    if not item:
        raise HTTPException(status_code=404, detail="Service item not found")

    for k, v in item_in.items():
        if hasattr(item, k):
            setattr(item, k, v)

    item.updated_at = datetime.utcnow()
    await item.save()
    return item


@router.delete("/catalogue/{item_id}")
async def delete_catalogue_item(
    item_id: str,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Delete a catalogue item."""
    item = await ServiceProduct.get(PydanticObjectId(item_id))
    if not item:
        raise HTTPException(status_code=404, detail="Service item not found")

    await item.delete()
    return {"status": "success", "message": "Catalogue item deleted"}


# ─── Maintenance Contracts Endpoints ──────────────────────────────────────────
@router.get("/contracts")
async def list_contracts(
    status: Optional[str] = None,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """List commercial maintenance contracts."""
    query = {}
    if status and status != "all":
        query["status"] = status
    contracts = await MaintenanceContract.find(query).sort("-created_at").to_list()
    return contracts


@router.post("/contracts")
async def create_contract(
    contract_in: dict,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Create a new commercial maintenance contract."""
    settings_doc = await get_or_create_settings()
    contract_number = f"{settings_doc.contract_prefix}{settings_doc.contract_next_number}"
    settings_doc.contract_next_number += 1
    await settings_doc.save()

    contract_data = {**contract_in, "contract_number": contract_number}
    
    # Calculate next_billing_date if not specified
    start_dt = datetime.fromisoformat(str(contract_data.get("start_date")).replace("Z", "")) if contract_data.get("start_date") else datetime.utcnow()
    if not contract_data.get("next_billing_date"):
        freq = contract_data.get("billing_frequency", "monthly")
        if freq == "monthly":
            next_date = start_dt + timedelta(days=30)
        elif freq == "quarterly":
            next_date = start_dt + timedelta(days=90)
        elif freq == "annually":
            next_date = start_dt + timedelta(days=365)
        else:
            next_date = start_dt + timedelta(days=30)
        contract_data["next_billing_date"] = next_date

    contract_data["start_date"] = start_dt
    contract = MaintenanceContract(**contract_data)
    await contract.create()

    await AuditLog(
        organization_id=contract.organization_id or getattr(current_user, "organization_id", "platform") or "platform",
        user_id=str(current_user.id),
        user_name=current_user.full_name or current_user.username,
        action="CREATE_MAINTENANCE_CONTRACT",
        resource_type="MaintenanceContract",
        resource_id=str(contract.id),
        details={"contract_number": contract.contract_number, "customer": contract.customer_name, "amount": contract.maintenance_amount},
    ).create()

    return contract


@router.get("/contracts/{contract_id}")
async def get_contract(
    contract_id: str,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    contract = await MaintenanceContract.get(PydanticObjectId(contract_id))
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.put("/contracts/{contract_id}")
async def update_contract(
    contract_id: str,
    contract_in: dict,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    contract = await MaintenanceContract.get(PydanticObjectId(contract_id))
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    for k, v in contract_in.items():
        if hasattr(contract, k):
            setattr(contract, k, v)

    contract.updated_at = datetime.utcnow()
    await contract.save()
    return contract


@router.post("/contracts/{contract_id}/trigger-invoice")
async def trigger_contract_invoice(
    contract_id: str,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Manually generate next recurring maintenance invoice for contract."""
    contract = await MaintenanceContract.get(PydanticObjectId(contract_id))
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    settings_doc = await get_or_create_settings()
    inv_number = f"{settings_doc.invoice_prefix}{settings_doc.invoice_next_number}"
    settings_doc.invoice_next_number += 1
    await settings_doc.save()

    inv_date = datetime.utcnow()
    due_date = inv_date + timedelta(days=contract.payment_terms_days or 14)

    item = CommercialInvoiceItem(
        description=f"Monthly Maintenance & Technical Support ({contract.contract_number})",
        billing_type=InvoiceBillingType.RECURRING,
        quantity=1.0,
        unit_price=contract.maintenance_amount,
        discount=0.0,
        tax_rate=0.0,
        tax_amount=0.0,
        total=contract.maintenance_amount,
    )

    invoice = CommercialInvoice(
        invoice_number=inv_number,
        organization_id=contract.organization_id,
        customer_name=contract.customer_name or "Commercial Customer",
        customer_email=contract.customer_email,
        customer_phone=contract.customer_phone,
        invoice_date=inv_date,
        due_date=due_date,
        currency=contract.currency or "XAF",
        contract_id=str(contract.id),
        items=[item],
        subtotal=contract.maintenance_amount,
        total_discount=0.0,
        total_tax=0.0,
        total_amount=contract.maintenance_amount,
        amount_paid=0.0,
        balance_due=contract.maintenance_amount,
        payment_status=CommercialPaymentStatus.UNPAID,
        status=CommercialInvoiceStatus.SENT,
        notes=f"Recurring maintenance invoice generated for contract {contract.contract_number}.",
    )
    await invoice.create()

    # Update contract next_billing_date
    contract.last_billed_date = inv_date
    if contract.billing_frequency == ContractBillingFrequency.MONTHLY:
        contract.next_billing_date = inv_date + timedelta(days=30)
    elif contract.billing_frequency == ContractBillingFrequency.QUARTERLY:
        contract.next_billing_date = inv_date + timedelta(days=90)
    elif contract.billing_frequency == ContractBillingFrequency.ANNUALLY:
        contract.next_billing_date = inv_date + timedelta(days=365)
    else:
        contract.next_billing_date = inv_date + timedelta(days=30)
    await contract.save()

    return invoice


# ─── Invoices Endpoints ───────────────────────────────────────────────────────
@router.get("/invoices")
async def list_invoices(
    status: Optional[str] = None,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """List commercial invoices."""
    query = {}
    if status and status != "all":
        query["status"] = status
    invoices = await CommercialInvoice.find(query).sort("-created_at").to_list()
    return invoices


@router.post("/invoices")
async def create_invoice(
    invoice_in: dict,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Create a new commercial invoice with server-side tax, discount, and balance calculations."""
    settings_doc = await get_or_create_settings()

    if not invoice_in.get("invoice_number"):
        inv_number = f"{settings_doc.invoice_prefix}{settings_doc.invoice_next_number}"
        settings_doc.invoice_next_number += 1
        await settings_doc.save()
        invoice_in["invoice_number"] = inv_number

    # Calculate item totals & invoice subtotal/taxes server-side
    raw_items = invoice_in.get("items", [])
    processed_items = []
    subtotal = 0.0
    total_tax = 0.0
    total_discount = 0.0

    for it in raw_items:
        qty = float(it.get("quantity", 1))
        price = float(it.get("unit_price", 0))
        disc = float(it.get("discount", 0))
        t_rate = float(it.get("tax_rate", 0))

        line_subtotal = (qty * price) - disc
        line_tax = (line_subtotal * t_rate) / 100.0 if t_rate > 0 else 0.0
        line_total = line_subtotal + line_tax

        subtotal += (qty * price)
        total_discount += disc
        total_tax += line_tax

        processed_items.append(CommercialInvoiceItem(
            description=it.get("description", "Item"),
            product_service_id=it.get("product_service_id"),
            product_service_code=it.get("product_service_code"),
            billing_type=it.get("billing_type", InvoiceBillingType.ONE_TIME),
            quantity=qty,
            show_quantity=bool(it.get("show_quantity", True)),
            unit_price=price,
            discount=disc,
            tax_rate=t_rate,
            tax_amount=line_tax,
            total=line_total,
        ))

    total_amount = subtotal - total_discount + total_tax
    amount_paid = float(invoice_in.get("amount_paid", 0))
    balance_due = max(0.0, total_amount - amount_paid)

    pay_status = CommercialPaymentStatus.UNPAID
    if amount_paid >= total_amount and total_amount > 0:
        pay_status = CommercialPaymentStatus.PAID
    elif amount_paid > 0:
        pay_status = CommercialPaymentStatus.PARTIALLY_PAID

    inv_date = datetime.fromisoformat(str(invoice_in.get("invoice_date")).replace("Z", "")) if invoice_in.get("invoice_date") else datetime.utcnow()
    due_date = datetime.fromisoformat(str(invoice_in.get("due_date")).replace("Z", "")) if invoice_in.get("due_date") else (inv_date + timedelta(days=settings_doc.default_payment_terms_days))

    invoice = CommercialInvoice(
        invoice_number=invoice_in["invoice_number"],
        organization_id=invoice_in.get("organization_id", ""),
        customer_name=invoice_in.get("customer_name", "Commercial Customer"),
        customer_email=invoice_in.get("customer_email"),
        customer_phone=invoice_in.get("customer_phone"),
        billing_address=invoice_in.get("billing_address"),
        invoice_date=inv_date,
        due_date=due_date,
        currency=invoice_in.get("currency", settings_doc.default_currency),
        contract_id=invoice_in.get("contract_id"),
        items=processed_items,
        subtotal=subtotal,
        total_discount=total_discount,
        total_tax=total_tax,
        total_amount=total_amount,
        amount_paid=amount_paid,
        balance_due=balance_due,
        payment_status=pay_status,
        status=invoice_in.get("status", CommercialInvoiceStatus.SENT),
        notes=invoice_in.get("notes"),
        terms_conditions=invoice_in.get("terms_conditions", settings_doc.default_terms_conditions),
    )
    await invoice.create()

    await AuditLog(
        organization_id=invoice.organization_id or getattr(current_user, "organization_id", "platform") or "platform",
        user_id=str(current_user.id),
        user_name=current_user.full_name or current_user.username,
        action="CREATE_COMMERCIAL_INVOICE",
        resource_type="CommercialInvoice",
        resource_id=str(invoice.id),
        details={"invoice_number": invoice.invoice_number, "total_amount": invoice.total_amount, "customer": invoice.customer_name},
    ).create()

    return invoice


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    invoice = await CommercialInvoice.get(PydanticObjectId(invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/invoices/{invoice_id}/status")
async def update_invoice_status(
    invoice_id: str,
    status_data: dict,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    invoice = await CommercialInvoice.get(PydanticObjectId(invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    new_status = status_data.get("status")
    if new_status:
        invoice.status = new_status
        invoice.updated_at = datetime.utcnow()
        await invoice.save()

    return invoice


@router.delete("/invoices/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Delete a commercial invoice."""
    invoice = await CommercialInvoice.get(PydanticObjectId(invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    await invoice.delete()

    await AuditLog(
        organization_id=invoice.organization_id or getattr(current_user, "organization_id", "platform") or "platform",
        user_id=str(current_user.id),
        user_name=current_user.full_name or current_user.username,
        action="DELETE_COMMERCIAL_INVOICE",
        resource_type="CommercialInvoice",
        resource_id=str(invoice.id),
        details={"invoice_number": invoice.invoice_number, "customer": invoice.customer_name},
    ).create()

    return {"status": "success", "message": "Invoice deleted"}


# ─── Payments & Reconciliation Endpoints ──────────────────────────────────────
@router.get("/payments")
async def list_payments(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """List commercial invoice payment records."""
    payments = await CommercialPayment.find_all().sort("-created_at").to_list()
    return payments


@router.post("/payments")
async def record_payment(
    payment_in: dict,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Record payment against invoice and recalculate payment status and balance due."""
    invoice_id = payment_in.get("invoice_id")
    invoice = await CommercialInvoice.get(PydanticObjectId(invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status == CommercialInvoiceStatus.CANCELLED or invoice.status == CommercialInvoiceStatus.VOID:
        raise HTTPException(status_code=400, detail="Cannot record payments on cancelled or void invoices")

    pay_amount = float(payment_in.get("amount", 0))
    if pay_amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than 0")

    if pay_amount > (invoice.balance_due + 0.01):
        raise HTTPException(status_code=400, detail=f"Payment amount ({pay_amount}) exceeds balance due ({invoice.balance_due})")

    # Generate payment number
    settings_doc = await get_or_create_settings()
    pay_number = f"PAY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    payment = CommercialPayment(
        payment_number=pay_number,
        invoice_id=str(invoice.id),
        invoice_number=invoice.invoice_number,
        organization_id=invoice.organization_id,
        customer_name=invoice.customer_name,
        amount=pay_amount,
        currency=invoice.currency,
        payment_method=payment_in.get("payment_method", CommercialPaymentMethod.BANK_TRANSFER),
        payment_date=datetime.utcnow(),
        reference_number=payment_in.get("reference_number"),
        notes=payment_in.get("notes"),
        recorded_by=str(current_user.full_name or current_user.username),
    )
    await payment.create()

    # Recalculate Invoice totals
    invoice.amount_paid += pay_amount
    invoice.balance_due = max(0.0, invoice.total_amount - invoice.amount_paid)

    if invoice.balance_due <= 0.01:
        invoice.payment_status = CommercialPaymentStatus.PAID
        invoice.status = CommercialInvoiceStatus.PAID
    else:
        invoice.payment_status = CommercialPaymentStatus.PARTIALLY_PAID
        invoice.status = CommercialInvoiceStatus.PARTIALLY_PAID

    invoice.updated_at = datetime.utcnow()
    await invoice.save()

    await AuditLog(
        organization_id=invoice.organization_id or getattr(current_user, "organization_id", "platform") or "platform",
        user_id=str(current_user.id),
        user_name=current_user.full_name or current_user.username,
        action="RECORD_COMMERCIAL_PAYMENT",
        resource_type="CommercialPayment",
        resource_id=str(payment.id),
        details={"payment_number": payment.payment_number, "amount": payment.amount, "invoice": invoice.invoice_number},
    ).create()

    return payment


# ─── Recurring Billing Engine ────────────────────────────────────────────────
@router.post("/recurring-billing/run")
async def run_recurring_billing(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Recurring Billing Engine: Checks active contracts whose next_billing_date <= today,
    generates next recurring invoice with idempotency check, and notifies admin.
    """
    now = datetime.utcnow()
    active_contracts = await MaintenanceContract.find(
        MaintenanceContract.status == ContractStatus.ACTIVE,
        MaintenanceContract.next_billing_date <= now
    ).to_list()

    generated_count = 0
    generated_invoices = []

    for contract in active_contracts:
        # Idempotency check: check if invoice already generated for contract in last 25 days
        cutoff = now - timedelta(days=25)
        existing = await CommercialInvoice.find_one({
            "contract_id": str(contract.id),
            "created_at": {"$gte": cutoff}
        })
        if existing:
            continue

        settings_doc = await get_or_create_settings()
        inv_number = f"{settings_doc.invoice_prefix}{settings_doc.invoice_next_number}"
        settings_doc.invoice_next_number += 1
        await settings_doc.save()

        due_date = now + timedelta(days=contract.payment_terms_days or 14)

        item = CommercialInvoiceItem(
            description=f"Monthly Maintenance & Technical Support ({contract.contract_number})",
            billing_type=InvoiceBillingType.RECURRING,
            quantity=1.0,
            unit_price=contract.maintenance_amount,
            discount=0.0,
            tax_rate=0.0,
            tax_amount=0.0,
            total=contract.maintenance_amount,
        )

        invoice = CommercialInvoice(
            invoice_number=inv_number,
            organization_id=contract.organization_id,
            customer_name=contract.customer_name or "Commercial Customer",
            customer_email=contract.customer_email,
            customer_phone=contract.customer_phone,
            invoice_date=now,
            due_date=due_date,
            currency=contract.currency or "XAF",
            contract_id=str(contract.id),
            items=[item],
            subtotal=contract.maintenance_amount,
            total_discount=0.0,
            total_tax=0.0,
            total_amount=contract.maintenance_amount,
            amount_paid=0.0,
            balance_due=contract.maintenance_amount,
            payment_status=CommercialPaymentStatus.UNPAID,
            status=CommercialInvoiceStatus.SENT,
            notes=f"Automated recurring maintenance invoice generated for contract {contract.contract_number}.",
        )
        await invoice.create()

        # Update contract dates
        contract.last_billed_date = now
        if contract.billing_frequency == ContractBillingFrequency.MONTHLY:
            contract.next_billing_date = now + timedelta(days=30)
        elif contract.billing_frequency == ContractBillingFrequency.QUARTERLY:
            contract.next_billing_date = now + timedelta(days=90)
        elif contract.billing_frequency == ContractBillingFrequency.ANNUALLY:
            contract.next_billing_date = now + timedelta(days=365)
        else:
            contract.next_billing_date = now + timedelta(days=30)
        await contract.save()

        # Alert
        await Alert(
            organization_id=contract.organization_id,
            type=AlertType.LOW_STOCK,  # reuse generic alert
            priority=AlertPriority.LOW,
            title=f"Recurring Invoice Generated: {invoice.invoice_number}",
            message=f"Maintenance invoice {invoice.invoice_number} ({contract.maintenance_amount} {contract.currency}) generated for {contract.customer_name}.",
            action_url=f"/commercial-billing",
        ).create()

        generated_count += 1
        generated_invoices.append(invoice.invoice_number)

    return {
        "status": "success",
        "generated_count": generated_count,
        "invoices": generated_invoices
    }


# ─── Commercial Dashboard & MRR Analytics ──────────────────────────────────────
@router.get("/dashboard-summary")
async def get_billing_dashboard_summary(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Billing Dashboard Summary: Financials, MRR, ARR, Active Contracts, and Overdue Receivables."""
    now = datetime.utcnow()
    invoices = await CommercialInvoice.find_all().to_list()
    contracts = await MaintenanceContract.find_all().to_list()
    organizations = await Organization.find_all().to_list()

    total_invoiced = sum(inv.total_amount for inv in invoices if inv.status != CommercialInvoiceStatus.CANCELLED)
    total_collected = sum(inv.amount_paid for inv in invoices if inv.status != CommercialInvoiceStatus.CANCELLED)
    total_outstanding = sum(inv.balance_due for inv in invoices if inv.status != CommercialInvoiceStatus.CANCELLED and inv.payment_status != CommercialPaymentStatus.PAID)

    # Overdue calculation
    overdue_invoices = [inv for inv in invoices if inv.balance_due > 0 and inv.due_date < now and inv.status != CommercialInvoiceStatus.CANCELLED]
    total_overdue = sum(inv.balance_due for inv in overdue_invoices)

    # Update overdue status on invoices dynamically
    for inv in overdue_invoices:
        if inv.status != CommercialInvoiceStatus.OVERDUE:
            inv.status = CommercialInvoiceStatus.OVERDUE
            await inv.save()

    # MRR calculation (Sum of active recurring contract monthly equivalent fees)
    mrr = 0.0
    active_contracts = [c for c in contracts if c.status == ContractStatus.ACTIVE]
    for c in active_contracts:
        amt = c.maintenance_amount
        if c.billing_frequency == ContractBillingFrequency.MONTHLY:
            mrr += amt
        elif c.billing_frequency == ContractBillingFrequency.QUARTERLY:
            mrr += (amt / 3.0)
        elif c.billing_frequency == ContractBillingFrequency.SEMI_ANNUALLY:
            mrr += (amt / 6.0)
        elif c.billing_frequency == ContractBillingFrequency.ANNUALLY:
            mrr += (amt / 12.0)

    arr = mrr * 12.0

    expiring_soon_count = len([c for c in contracts if c.status == ContractStatus.ACTIVE and c.end_date and (c.end_date - now).days <= 30])
    grace_period_count = len([c for c in contracts if c.service_status == ServiceStatus.GRACE_PERIOD or c.service_status == ServiceStatus.OVERDUE])

    return {
        "financials": {
            "total_invoiced": total_invoiced,
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
            "total_overdue": total_overdue,
            "currency": "XAF"
        },
        "mrr_arr": {
            "mrr": mrr,
            "arr": arr,
            "active_contracts_count": len(active_contracts),
            "avg_contract_value": (mrr / len(active_contracts)) if len(active_contracts) > 0 else 0.0
        },
        "contracts_summary": {
            "total_contracts": len(contracts),
            "active_contracts": len(active_contracts),
            "expiring_soon": expiring_soon_count,
            "grace_period_count": grace_period_count,
        },
        "customers_summary": {
            "total_customers": len(organizations),
            "active_customers": len([o for o in organizations if o.status == "active"]),
        },
        "recent_overdue_invoices": [
            {
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "customer_name": inv.customer_name,
                "due_date": inv.due_date,
                "balance_due": inv.balance_due,
                "currency": inv.currency,
                "days_overdue": (now - inv.due_date).days
            } for inv in overdue_invoices[:5]
        ]
    }


# ─── Commercial Settings Endpoints ────────────────────────────────────────────
@router.get("/settings")
async def get_settings(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    return await get_or_create_settings()


@router.post("/settings")
async def update_settings(
    settings_in: dict,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    settings_doc = await get_or_create_settings()
    for k, v in settings_in.items():
        if hasattr(settings_doc, k):
            setattr(settings_doc, k, v)
    settings_doc.updated_at = datetime.utcnow()
    await settings_doc.save()
    return settings_doc
