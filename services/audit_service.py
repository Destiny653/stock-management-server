"""Audit Log Service - Utility helper to record audit events"""
from typing import Optional, Dict, Any
from models.audit_log import AuditLog


async def log_audit_event(
    organization_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """Record an audit log entry in the database asynchronously."""
    audit_entry = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        user_name=user_name,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before_state=before_state,
        after_state=after_state,
        reason=reason,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await audit_entry.insert()
    return audit_entry
