"""Finance API Endpoints - Financial ledger metrics and executive accounting reports"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import date
from models.user import User
from api.deps import get_current_user
from services.finance_service import get_financial_summary

router = APIRouter()


@router.get("/summary")
async def get_finance_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Retrieve organization financial ledger summary (Revenue, COGS, Gross Profit, Payables, Receivables)."""
    org_id = str(current_user.organization_id)
    return await get_financial_summary(org_id, start_date, end_date)
