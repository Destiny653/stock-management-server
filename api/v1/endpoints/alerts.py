"""Alert endpoints"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from beanie import PydanticObjectId
from api import deps
from models.user import User
from models.alert import Alert
from schemas.alert import AlertCreate, AlertUpdate, AlertResponse

router = APIRouter()


@router.get("/", response_model=List[AlertResponse])
async def read_alerts(
    skip: int = 0,
    limit: int = 100,
    alert_type: Optional[str] = None,
    priority: Optional[str] = None,
    is_read: Optional[bool] = None,
    is_dismissed: Optional[bool] = None,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve alerts. Filtered by organization for non-superadmins.
    """
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
    
    if alert_type:
        query["type"] = alert_type
    if priority:
        query["priority"] = priority
    if is_read is not None:
        query["is_read"] = is_read
    if is_dismissed is not None:
        query["is_dismissed"] = is_dismissed
    
    alerts = await Alert.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
    return alerts


@router.post("/", response_model=AlertResponse)
async def create_alert(
    alert_in: AlertCreate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new alert within an organization.
    """
    data = alert_in.model_dump()
    if organization_id:
        data["organization_id"] = organization_id
        
    alert = Alert(**data)
    await alert.create()
    return alert


@router.get("/{alert_id}", response_model=AlertResponse)
async def read_alert(
    alert_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get alert by ID within an organization.
    """
    query = {"_id": PydanticObjectId(alert_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    alert = await Alert.find_one(query)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    alert_in: AlertUpdate,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update an alert (mark as read/dismissed).
    """
    query = {"_id": PydanticObjectId(alert_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    alert = await Alert.find_one(query)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    update_data = alert_in.model_dump(exclude_unset=True)
    # Prevent organization_id modification
    if "organization_id" in update_data:
        del update_data["organization_id"]
        
    await alert.update({"$set": update_data})
    await alert.save()
    return alert


@router.delete("/{alert_id}", response_model=AlertResponse)
async def delete_alert(
    alert_id: str,
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete an alert within an organization.
    """
    query = {"_id": PydanticObjectId(alert_id)}
    if organization_id:
        query["organization_id"] = organization_id
        
    alert = await Alert.find_one(query)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await alert.delete()
    return alert


@router.post("/mark-all-read", response_model=dict)
async def mark_all_alerts_read(
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Mark all alerts as read for an organization.
    """
    query = {"is_read": False}
    if organization_id:
        query["organization_id"] = organization_id
        
    result = await Alert.find(query).update_many({"$set": {"is_read": True}})
    
    return {"message": f"Marked {result.modified_count} alerts as read"}


@router.get("/unread/count", response_model=dict)
async def get_unread_count(
    organization_id: Optional[str] = Depends(deps.get_organization_id),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get count of unread alerts for an organization.
    """
    query = {
        "is_read": False,
        "is_dismissed": False
    }
    if organization_id:
        query["organization_id"] = organization_id
        
    count = await Alert.find(query).count()
    
    return {"unread_count": count}
