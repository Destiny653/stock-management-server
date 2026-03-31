"""Helper functions for notification management"""
from typing import List
from models.user import User, UserRole


async def get_org_notification_recipients(organization_id: str) -> List[User]:
    """
    Get all users in an organization who should receive administrative notifications 
    (Admins and Managers).
    """
    if not organization_id:
        return []
        
    recipients = await User.find({
        "organization_id": organization_id,
        "role": {"$in": [UserRole.ADMIN, UserRole.MANAGER]},
        "is_active": True
    }).to_list()
    
    return recipients
