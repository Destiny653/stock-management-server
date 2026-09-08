"""Stock Transfers API Endpoints – Implements 6-Stage Transfer Lifecycle and Immutable Ledger Logging"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from beanie import PydanticObjectId

from models.user import User
from models.location import Location
from models.location_stock import LocationStock
from models.stock_transfer import StockTransfer, TransferStatus, TransferItem
from models.stock_movement import StockMovement, MovementType
from models.product import Product
from api.deps import get_current_user

router = APIRouter()


async def _get_or_create_stock(org_id: str, location_id: str, product_id: str) -> LocationStock:
    """Helper to retrieve or initialize a LocationStock record."""
    stock = await LocationStock.find_one({
        "organization_id": org_id,
        "location_id": location_id,
        "product_id": product_id
    })
    if not stock:
        p = await Product.find_one({"_id": PydanticObjectId(product_id)}) if PydanticObjectId.is_valid(product_id) else None
        stock = LocationStock(
            organization_id=org_id,
            location_id=location_id,
            product_id=product_id,
            sku=p.sku if p else None,
            product_name=p.name if p else "Product",
            on_hand=p.total_stock if p else 0,
            available=p.total_stock if p else 0,
            unit_cost=p.cost_price if p else 0.0
        )
        await stock.insert()
    return stock


@router.get("/")
async def list_transfers(
    status_filter: Optional[str] = None,
    location_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> Any:
    """List stock transfers for the organization.
    Optionally scoped to transfers involving a specific location (as source or destination).
    """
    query: dict = {"organization_id": current_user.organization_id}
    if status_filter:
        query["status"] = status_filter
    if location_id:
        query["$or"] = [
            {"from_location_id": location_id},
            {"to_location_id": location_id},
        ]

    transfers = await StockTransfer.find(query).sort("-created_at").to_list()
    result = []
    for t in transfers:
        d = t.model_dump()
        d["id"] = str(t.id)
        result.append(d)
    return result


@router.post("/request", status_code=status.HTTP_201_CREATED)
async def create_transfer_request(
    data: dict,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Create a new transfer request (Status: REQUESTED)."""
    from_loc_id = data.get("from_location_id")
    to_loc_id = data.get("to_location_id")
    items_raw = data.get("items", [])

    if not from_loc_id or not to_loc_id:
        raise HTTPException(status_code=400, detail="Source and destination locations are required")
    if from_loc_id == to_loc_id:
        raise HTTPException(status_code=400, detail="Source and destination locations must be different")
    if not items_raw:
        raise HTTPException(status_code=400, detail="At least one transfer item is required")

    from_loc = await Location.find_one({"_id": PydanticObjectId(from_loc_id)}) if PydanticObjectId.is_valid(from_loc_id) else None
    to_loc = await Location.find_one({"_id": PydanticObjectId(to_loc_id)}) if PydanticObjectId.is_valid(to_loc_id) else None

    if not from_loc or not to_loc:
        raise HTTPException(status_code=404, detail="Source or destination location not found")

    items: List[TransferItem] = []
    for raw in items_raw:
        pid = raw.get("product_id")
        qty = int(raw.get("qty_requested", 1))
        p = await Product.find_one({"_id": PydanticObjectId(pid)}) if PydanticObjectId.is_valid(pid) else None
        
        items.append(TransferItem(
            product_id=pid,
            product_name=p.name if p else raw.get("product_name", "Product"),
            sku=p.sku if p else raw.get("sku"),
            qty_requested=qty,
            unit_cost=p.cost_price if p else 0.0,
            total_cost=(p.cost_price * qty) if p else 0.0
        ))

    trf_no = f"TRF-{datetime.utcnow().strftime('%Y%m%d')}-{datetime.utcnow().strftime('%H%M%S')}"

    transfer = StockTransfer(
        transfer_number=trf_no,
        organization_id=current_user.organization_id,
        from_location_id=from_loc_id,
        from_location_name=from_loc.name,
        to_location_id=to_loc_id,
        to_location_name=to_loc.name,
        status=TransferStatus.REQUESTED,
        items=items,
        requested_by_id=str(current_user.id),
        requested_by_name=current_user.full_name or current_user.email,
        notes=data.get("notes")
    )
    await transfer.insert()
    
    res = transfer.model_dump()
    res["id"] = str(transfer.id)
    return res


@router.post("/{transfer_id}/approve")
async def approve_transfer(
    transfer_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Approve a transfer request (Status: APPROVED)."""
    transfer = await StockTransfer.find_one({"_id": PydanticObjectId(transfer_id), "organization_id": current_user.organization_id})
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.status != TransferStatus.REQUESTED:
        raise HTTPException(status_code=400, detail=f"Cannot approve transfer in {transfer.status} state")

    transfer.status = TransferStatus.APPROVED
    transfer.approved_by_id = str(current_user.id)
    transfer.approved_by_name = current_user.full_name or current_user.email
    transfer.approved_at = datetime.utcnow()
    await transfer.save()

    res = transfer.model_dump()
    res["id"] = str(transfer.id)
    return res


@router.post("/{transfer_id}/dispatch")
async def dispatch_transfer(
    transfer_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Dispatch stock from source location (Status: DISPATCHED / IN_TRANSIT).
    Deducts available stock from source location and places items into in_transit state."""
    transfer = await StockTransfer.find_one({"_id": PydanticObjectId(transfer_id), "organization_id": current_user.organization_id})
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.status not in [TransferStatus.REQUESTED, TransferStatus.APPROVED]:
        raise HTTPException(status_code=400, detail=f"Cannot dispatch transfer in {transfer.status} state")

    dispatch_items = data.get("items", [])
    dispatch_map = {item["product_id"]: int(item.get("qty_dispatched", item.get("qty_requested", 0))) for item in dispatch_items}

    # Process inventory movements for each item
    for item in transfer.items:
        qty_to_dispatch = dispatch_map.get(item.product_id, item.qty_requested)
        item.qty_dispatched = qty_to_dispatch
        
        # Source location stock update
        src_stock = await _get_or_create_stock(transfer.organization_id, transfer.from_location_id, item.product_id)
        before_avail = src_stock.available
        src_stock.available = max(0, src_stock.available - qty_to_dispatch)
        src_stock.in_transit += qty_to_dispatch
        src_stock.updated_at = datetime.utcnow()
        await src_stock.save()

        # Destination location stock update (mark as in_transit)
        dest_stock = await _get_or_create_stock(transfer.organization_id, transfer.to_location_id, item.product_id)
        dest_stock.in_transit += qty_to_dispatch
        dest_stock.updated_at = datetime.utcnow()
        await dest_stock.save()

        # Write immutable audit log entry
        m = StockMovement(
            organization_id=transfer.organization_id,
            product_id=item.product_id,
            product_name=item.product_name,
            sku=item.sku,
            type=MovementType.TRANSFER_DISPATCH,
            quantity=-qty_to_dispatch,
            before_quantity=before_avail,
            after_quantity=src_stock.available,
            from_location=transfer.from_location_name,
            to_location=transfer.to_location_name,
            from_location_id=transfer.from_location_id,
            to_location_id=transfer.to_location_id,
            reference=transfer.transfer_number,
            notes=f"Dispatched in-transit stock transfer {transfer.transfer_number}",
            unit_cost=item.unit_cost,
            total_cost=item.unit_cost * qty_to_dispatch,
            performed_by=current_user.email,
            actor_id=str(current_user.id),
            actor_name=current_user.full_name or current_user.email
        )
        await m.insert()

    transfer.status = TransferStatus.DISPATCHED
    transfer.dispatched_by_id = str(current_user.id)
    transfer.dispatched_by_name = current_user.full_name or current_user.email
    transfer.dispatched_at = datetime.utcnow()
    transfer.tracking_ref = data.get("tracking_ref")
    await transfer.save()

    res = transfer.model_dump()
    res["id"] = str(transfer.id)
    return res


@router.post("/{transfer_id}/receive")
async def receive_transfer(
    transfer_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Receive dispatched stock at destination location (Status: RECEIVED / COMPLETED).
    Supports partial receiving, damaged, or rejected quantities."""
    transfer = await StockTransfer.find_one({"_id": PydanticObjectId(transfer_id), "organization_id": current_user.organization_id})
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.status not in [TransferStatus.DISPATCHED, TransferStatus.IN_TRANSIT]:
        raise HTTPException(status_code=400, detail=f"Cannot receive transfer in {transfer.status} state")

    received_items = data.get("items", [])
    rec_map = {
        item["product_id"]: {
            "qty_received": int(item.get("qty_received", 0)),
            "qty_damaged": int(item.get("qty_damaged", 0)),
            "qty_rejected": int(item.get("qty_rejected", 0))
        }
        for item in received_items
    }

    all_completed = True

    for item in transfer.items:
        rec_data = rec_map.get(item.product_id, {
            "qty_received": item.qty_dispatched,
            "qty_damaged": 0,
            "qty_rejected": 0
        })

        qty_received = rec_data["qty_received"]
        qty_damaged = rec_data["qty_damaged"]
        qty_rejected = rec_data["qty_rejected"]

        item.qty_received = qty_received
        item.qty_damaged = qty_damaged
        item.qty_rejected = qty_rejected

        dispatched_total = item.qty_dispatched

        # Clear in-transit from source & deduct physical on_hand
        src_stock = await _get_or_create_stock(transfer.organization_id, transfer.from_location_id, item.product_id)
        src_stock.in_transit = max(0, src_stock.in_transit - dispatched_total)
        src_stock.on_hand = max(0, src_stock.on_hand - (qty_received + qty_damaged))
        src_stock.updated_at = datetime.utcnow()
        await src_stock.save()

        # Update destination stock: clear in_transit, add available & on_hand
        dest_stock = await _get_or_create_stock(transfer.organization_id, transfer.to_location_id, item.product_id)
        before_avail = dest_stock.available
        dest_stock.in_transit = max(0, dest_stock.in_transit - dispatched_total)
        dest_stock.available += qty_received
        dest_stock.on_hand += qty_received
        dest_stock.damaged += qty_damaged
        dest_stock.updated_at = datetime.utcnow()
        await dest_stock.save()

        # Log receipt movement
        m_rec = StockMovement(
            organization_id=transfer.organization_id,
            product_id=item.product_id,
            product_name=item.product_name,
            sku=item.sku,
            type=MovementType.TRANSFER_RECEIPT,
            quantity=qty_received,
            before_quantity=before_avail,
            after_quantity=dest_stock.available,
            from_location=transfer.from_location_name,
            to_location=transfer.to_location_name,
            from_location_id=transfer.from_location_id,
            to_location_id=transfer.to_location_id,
            reference=transfer.transfer_number,
            notes=f"Received stock transfer {transfer.transfer_number}",
            unit_cost=item.unit_cost,
            total_cost=item.unit_cost * qty_received,
            performed_by=current_user.email,
            actor_id=str(current_user.id),
            actor_name=current_user.full_name or current_user.email
        )
        await m_rec.insert()

        # Log damaged movement if any
        if qty_damaged > 0:
            m_dam = StockMovement(
                organization_id=transfer.organization_id,
                product_id=item.product_id,
                product_name=item.product_name,
                sku=item.sku,
                type=MovementType.TRANSFER_DAMAGED,
                quantity=qty_damaged,
                from_location=transfer.from_location_name,
                to_location=transfer.to_location_name,
                reference=transfer.transfer_number,
                notes=f"Damaged stock received on transfer {transfer.transfer_number}",
                unit_cost=item.unit_cost,
                total_cost=item.unit_cost * qty_damaged,
                performed_by=current_user.email
            )
            await m_dam.insert()

    transfer.status = TransferStatus.COMPLETED
    transfer.received_by_id = str(current_user.id)
    transfer.received_by_name = current_user.full_name or current_user.email
    transfer.received_at = datetime.utcnow()
    transfer.completed_at = datetime.utcnow()
    await transfer.save()

    res = transfer.model_dump()
    res["id"] = str(transfer.id)
    return res


@router.post("/{transfer_id}/cancel")
async def cancel_transfer(
    transfer_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Cancel a transfer request and reconcile in-transit stock if dispatched."""
    transfer = await StockTransfer.find_one({"_id": PydanticObjectId(transfer_id), "organization_id": current_user.organization_id})
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.status in [TransferStatus.COMPLETED, TransferStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail=f"Transfer is already {transfer.status}")

    # Reconcile in-transit stock if transfer was dispatched
    if transfer.status == TransferStatus.DISPATCHED:
        for item in transfer.items:
            dispatched = item.qty_dispatched
            if dispatched > 0:
                src_stock = await _get_or_create_stock(transfer.organization_id, transfer.from_location_id, item.product_id)
                src_stock.in_transit = max(0, src_stock.in_transit - dispatched)
                src_stock.available += dispatched
                await src_stock.save()

                dest_stock = await _get_or_create_stock(transfer.organization_id, transfer.to_location_id, item.product_id)
                dest_stock.in_transit = max(0, dest_stock.in_transit - dispatched)
                await dest_stock.save()

    transfer.status = TransferStatus.CANCELLED
    transfer.cancelled_at = datetime.utcnow()
    await transfer.save()

    res = transfer.model_dump()
    res["id"] = str(transfer.id)
    return res
