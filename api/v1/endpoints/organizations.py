"""Organization endpoints"""
from typing import List, Any, Optional, Dict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from beanie import PydanticObjectId
from bson import ObjectId as BsonObjectId
import json
from api import deps
from models.user import User
from models.organization import Organization, OrganizationStatus
from models.product import Product
from models.supplier import Supplier
from models.vendor import Vendor
from models.warehouse import Warehouse
from models.purchase_order import PurchaseOrder
from models.sale import Sale
from models.stock_movement import StockMovement
from models.alert import Alert
from models.vendor_payment import VendorPayment
from models.organization_payment import OrganizationPayment
from schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from services.subscription_notifications import (
    create_org_approved_notification,
    create_trial_extended_notification,
    create_storage_capacity_changed_notification,
)

router = APIRouter()

ORG_SCOPED_MODELS = [
    User,
    Product,
    Supplier,
    Vendor,
    Warehouse,
    PurchaseOrder,
    Sale,
    StockMovement,
    Alert,
    VendorPayment,
    OrganizationPayment,
]


async def _estimate_org_storage_usage_kb(organization_id: str) -> Dict[str, Any]:
    usage_by_collection: Dict[str, int] = {}
    total_bytes = 0

    for model in ORG_SCOPED_MODELS:
        # get_motor_collection() is the correct Beanie method for the Motor collection
        collection = model.get_motor_collection()
        docs = await collection.find({"organization_id": organization_id}).to_list(length=None)
        collection_bytes = 0
        for doc in docs:
            # Motor returns plain dicts; estimate byte size via JSON serialisation
            # (a reasonable BSON-size proxy — accurate to within ~10%)
            try:
                collection_bytes += len(json.dumps(doc, default=str).encode("utf-8"))
            except Exception:
                collection_bytes += 512  # fallback estimate per document
        usage_by_collection[model.get_settings().name] = collection_bytes
        total_bytes += collection_bytes

    return {
        "total_bytes": total_bytes,
        "total_kb": round(total_bytes / 1024, 2),
        "by_collection_bytes": usage_by_collection,
    }


@router.get("/", response_model=List[OrganizationResponse])
async def read_organizations(
    skip: int = 0,
    limit: int = 100,
    id: Optional[str] = None,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Retrieve all organizations (admin only).
    """
    query = {}
    if id:
        query["_id"] = PydanticObjectId(id)
    organizations = await Organization.find(query).skip(skip).limit(limit).to_list()
    # Keep frontend-aligned fields in sync with older DB field names.
    for org in organizations:
        if org.subscription_plan is None and org.subscription_plan_id:
            org.subscription_plan = org.subscription_plan_id
        if org.billing_cycle == "monthly" and org.subscription_interval and org.subscription_interval != "monthly":
            org.billing_cycle = org.subscription_interval
    return organizations


@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    organization_in: OrganizationCreate,
) -> Any:
    """
    Create new organization (Public for registration).
    """
    org = await Organization.find_one(Organization.code == organization_in.code)
    if org:
        raise HTTPException(
            status_code=400,
            detail="An organization with this code already exists",
        )
    data = organization_in.model_dump()

    # New org registration: start in "pending" until platform-staff approves,
    # and grant a 30-day free trial by default.
    data.setdefault("status", "pending")
    if not data.get("trial_ends_at"):
        data["trial_ends_at"] = datetime.utcnow() + timedelta(days=30)
    # Normalize newer -> backward-compatible fields.
    if data.get("subscription_plan") and not data.get("subscription_plan_id"):
        data["subscription_plan_id"] = data["subscription_plan"]
    if data.get("billing_cycle") and not data.get("subscription_interval"):
        data["subscription_interval"] = data["billing_cycle"]
    organization = Organization(**data)
    await organization.create()
    return organization


@router.get("/all/storage/overview", response_model=Dict[str, Any])
async def get_storage_overview(
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Get platform storage overview and per-organization usage (platform admin only).
    """
    organizations = await Organization.find({}).to_list()
    org_summaries = []
    total_used_kb = 0.0
    total_capacity_kb = 0

    for org in organizations:
        usage = await _estimate_org_storage_usage_kb(str(org.id))
        used_kb = float(usage.get("total_kb", 0))
        capacity_kb = int(org.storage_capacity_kb or 0)
        total_used_kb += used_kb
        total_capacity_kb += capacity_kb
        
        usage_percent = round((used_kb / capacity_kb) * 100, 2) if capacity_kb > 0 else None
        
        org_summaries.append(
            {
                "organization_id": str(org.id),
                "organization_name": org.name,
                "used_kb": used_kb,
                "capacity_kb": capacity_kb,
                "usage_percent": usage_percent,
            }
        )

    return {
        "total_organizations": len(organizations),
        "total_used_kb": round(total_used_kb, 2),
        "total_capacity_kb": total_capacity_kb,
        "overall_usage_percent": round((total_used_kb / total_capacity_kb) * 100, 2) if total_capacity_kb > 0 else None,
        "organizations": org_summaries,
    }


@router.get("/all/storage/db-stats", response_model=Dict[str, Any])
async def get_database_stats(
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Get full MongoDB database storage statistics (platform admin only).
    Returns the actual database size, storage allocation, index sizes, etc.
    """
    try:
        # Access the underlying motor database via any Beanie model's collection
        db = Organization.get_motor_collection().database
        stats = await db.command("dbStats")

        # Robustly handle fields that might be None or missing in Atlas
        def get_stat(key: str) -> float:
            val = stats.get(key)
            return float(val) if val is not None else 0.0

        data_size_kb = round(get_stat("dataSize") / 1024, 2)
        storage_size_kb = round(get_stat("storageSize") / 1024, 2)
        index_size_kb = round(get_stat("indexSize") / 1024, 2)
        total_size_kb = round(get_stat("totalSize") / 1024, 2)
        fs_used_kb = round(get_stat("fsUsedSize") / 1024, 2)
        fs_total_kb = round(get_stat("fsTotalSize") / 1024, 2)

        return {
            "db_name": stats.get("db", ""),
            "collections": int(stats.get("collections", 0)),
            "objects": int(stats.get("objects", 0)),
            "data_size_kb": data_size_kb,
            "storage_size_kb": storage_size_kb,
            "index_size_kb": index_size_kb,
            "total_size_kb": total_size_kb,
            "fs_used_size_kb": fs_used_kb,
            "fs_total_size_kb": fs_total_kb,
            "fs_available_kb": round(max(0, fs_total_kb - fs_used_kb), 2),
            "ok": bool(stats.get("ok", 1))
        }
    except Exception as e:
        import logging
        logging.error(f"Error fetching database stats: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Database statistics could not be retrieved: {str(e)}"
        )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def read_organization(
    organization_id: str,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get organization by ID.
    """
    if not BsonObjectId.is_valid(organization_id):
        raise HTTPException(status_code=400, detail="Invalid organization ID format")
    # Platform-staff can access any organization, business-staff must belong to this org
    if current_user.user_type != "platform-staff" and current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this organization's data"
        )
        
    organization = await Organization.get(organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    if organization.subscription_plan is None and organization.subscription_plan_id:
        organization.subscription_plan = organization.subscription_plan_id
    if organization.billing_cycle == "monthly" and organization.subscription_interval and organization.subscription_interval != "monthly":
        organization.billing_cycle = organization.subscription_interval
    return organization


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str,
    organization_in: OrganizationUpdate,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Update an organization (admin only).
    """
    organization = await Organization.get(organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    update_data = organization_in.model_dump(exclude_unset=True)

    # Map frontend billing fields -> backward-compatible DB fields.
    if update_data.get("subscription_plan") and not update_data.get("subscription_plan_id"):
        update_data["subscription_plan_id"] = update_data["subscription_plan"]
    if update_data.get("billing_cycle") and not update_data.get("subscription_interval"):
        update_data["subscription_interval"] = update_data["billing_cycle"]

    await organization.update({"$set": update_data})
    await organization.save()
    return organization


@router.post("/{organization_id}/approve", response_model=OrganizationResponse)
async def approve_organization(
    organization_id: str,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Approve an organization so it can start using paid features/transactions (platform admin only).
    """
    organization = await Organization.get(organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    organization.status = OrganizationStatus.ACTIVE
    organization.updated_at = datetime.utcnow()
    await organization.save()

    await create_org_approved_notification(
        organization=organization,
        action_url=f"Dashboard",
    )

    return organization


@router.post("/{organization_id}/extend-trial", response_model=OrganizationResponse)
async def extend_trial(
    organization_id: str,
    days: int = 30,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Extend an organization's free trial by N days (platform admin only).
    """
    if days <= 0 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")

    organization = await Organization.get(organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    base = organization.trial_ends_at or datetime.utcnow()
    if base < datetime.utcnow():
        base = datetime.utcnow()
    organization.trial_ends_at = base + timedelta(days=days)
    organization.updated_at = datetime.utcnow()
    await organization.save()

    await create_trial_extended_notification(
        organization=organization,
        new_trial_end=organization.trial_ends_at,
        days_added=days,
        action_url="Dashboard",
    )
    return organization


@router.put("/{organization_id}/storage-capacity", response_model=OrganizationResponse)
async def set_storage_capacity(
    organization_id: str,
    storage_capacity_kb: int,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Update organization storage capacity/quota in KB (platform admin only).
    """
    if storage_capacity_kb <= 0:
        raise HTTPException(status_code=400, detail="storage_capacity_kb must be > 0")

    organization = await Organization.get(organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    organization.storage_capacity_kb = storage_capacity_kb
    organization.updated_at = datetime.utcnow()
    await organization.save()

    await create_storage_capacity_changed_notification(
        organization=organization,
        new_capacity_kb=storage_capacity_kb,
        action_url="Dashboard",
    )

    return organization


@router.get("/{organization_id}/storage-summary", response_model=dict)
async def get_organization_storage_summary(
    organization_id: str,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Get storage usage summary for one organization (platform admin only).
    """
    if not BsonObjectId.is_valid(organization_id):
        raise HTTPException(status_code=400, detail="Invalid organization ID format")
    organization = await Organization.get(organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    usage = await _estimate_org_storage_usage_kb(organization_id)
    capacity_kb = organization.storage_capacity_kb or 0
    used_kb = usage["total_kb"]
    usage_percent = round((used_kb / capacity_kb) * 100, 2) if capacity_kb > 0 else None

    return {
        "organization_id": organization_id,
        "organization_name": organization.name,
        "capacity_kb": capacity_kb,
        "used_kb": used_kb,
        "usage_percent": usage_percent,
        "by_collection_bytes": usage["by_collection_bytes"],
    }

@router.delete("/{organization_id}", response_model=OrganizationResponse)
async def delete_organization(
    organization_id: str,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Delete an organization (admin only).
    """
    organization = await Organization.get(organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    await organization.delete()
    return organization
