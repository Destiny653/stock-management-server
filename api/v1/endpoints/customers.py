"""Customer API Endpoints - Customer directory, credit balance, and history"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from models.user import User
from models.customer import Customer
from api.deps import get_current_user
from services.audit_service import log_audit_event

router = APIRouter()


@router.get("", response_model=List[Customer])
async def list_customers(
    current_user: User = Depends(get_current_user),
):
    """Retrieve list of customers for the organization."""
    org_id = str(current_user.organization_id)
    return await Customer.find(Customer.organization_id == org_id).to_list()


@router.post("", response_model=Customer)
async def create_customer(
    customer_data: dict,
    current_user: User = Depends(get_current_user),
):
    """Create a new customer profile."""
    org_id = str(current_user.organization_id)
    
    # Auto-generate code if missing
    code = customer_data.get("code")
    if not code:
        count = await Customer.find(Customer.organization_id == org_id).count()
        code = f"CUST-{count + 1:04d}"

    customer = Customer(
        organization_id=org_id,
        name=customer_data["name"],
        code=code,
        email=customer_data.get("email"),
        phone=customer_data.get("phone"),
        address=customer_data.get("address"),
        city=customer_data.get("city"),
        country=customer_data.get("country"),
        tax_id=customer_data.get("tax_id"),
        credit_limit=float(customer_data.get("credit_limit") or 0.0),
        notes=customer_data.get("notes"),
    )
    await customer.insert()

    await log_audit_event(
        organization_id=org_id,
        action="customer.create",
        resource_type="Customer",
        resource_id=str(customer.id),
        user_id=str(current_user.id),
        user_name=current_user.username,
        reason=f"Created customer '{customer.name}'",
    )

    return customer


@router.get("/{customer_id}", response_model=Customer)
async def get_customer(
    customer_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get single customer profile."""
    customer = await Customer.get(customer_id)
    if not customer or str(customer.organization_id) != str(current_user.organization_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer
