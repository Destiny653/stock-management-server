"""Unified Locations & Location Stock Management API Endpoints"""
from typing import List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from beanie import PydanticObjectId

from models.user import User
from models.location import Location, LocationType, LocationStatus
from models.location_stock import LocationStock
from models.pos_terminal import POSTerminal, POSTerminalStatus
from models.product import Product
from models.warehouse import Warehouse
from api.deps import get_current_user

router = APIRouter()


@router.get("/")
async def get_locations(
    type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get all locations for the current organization."""
    query: dict = {"organization_id": current_user.organization_id}
    if type:
        query["type"] = type
    if status:
        query["status"] = status

    locations = await Location.find(query).to_list()
    
    # If no locations exist yet, auto-seed default Store & Warehouse from existing legacy data
    if not locations and current_user.organization_id:
        from models.organization import Organization
        org = await Organization.get(current_user.organization_id)
        org_city = (org and org.city) or "Douala"
        org_country = (org and org.country) or "Cameroon"
        org_phone = (org and org.phone) or None
        org_email = (org and org.email) or None
        org_name = (org and org.name) or None

        # Check existing warehouses
        warehouses = await Warehouse.find({"organization_id": current_user.organization_id}).to_list()
        if warehouses:
            for w in warehouses:
                loc = Location(
                    organization_id=current_user.organization_id,
                    name=w.name,
                    code=w.code or "LOC-01",
                    type=LocationType.WAREHOUSE,
                    status=LocationStatus.ACTIVE,
                    address="",
                    city=org_city,
                    country=org_country,
                    phone=org_phone,
                    email=org_email,
                    is_central_hub=w.is_central_hub
                )
                await loc.insert()
                locations.append(loc)
        else:
            main_warehouse = Location(
                organization_id=current_user.organization_id,
                name=f"{org_name} Central Warehouse" if org_name else "Main Central Warehouse",
                code="WH-MAIN",
                type=LocationType.WAREHOUSE,
                status=LocationStatus.ACTIVE,
                address="Central Industrial Zone",
                city=org_city,
                country=org_country,
                phone=org_phone,
                email=org_email,
                latitude=4.0511,
                longitude=9.7679,
                is_central_hub=True
            )
            main_store = Location(
                organization_id=current_user.organization_id,
                name=f"{org_name} Store" if org_name else "Primary Retail Store",
                code="STR-01",
                type=LocationType.STORE,
                status=LocationStatus.ACTIVE,
                address="Commercial Avenue",
                city=org_city,
                country=org_country,
                phone=org_phone,
                email=org_email,
                latitude=4.0550,
                longitude=9.7700,
                allow_pos=True
            )
            await main_warehouse.insert()
            await main_store.insert()
            locations = [main_warehouse, main_store]

    # Include stats for each location
    result = []
    for loc in locations:
        loc_id = str(loc.id)
        stocks = await LocationStock.find({"location_id": loc_id}).to_list()
        total_items = len(stocks)
        total_on_hand = sum(s.on_hand for s in stocks)
        total_available = sum(s.available for s in stocks)
        total_in_transit = sum(s.in_transit for s in stocks)
        
        terminals = await POSTerminal.find({"store_id": loc_id}).to_list()
        
        doc = loc.model_dump()
        doc["id"] = loc_id
        doc["total_items"] = total_items
        doc["total_on_hand"] = total_on_hand
        doc["total_available"] = total_available
        doc["total_in_transit"] = total_in_transit
        doc["terminal_count"] = len(terminals)
        result.append(doc)

    return result


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_location(
    data: dict,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Create a new unified location (Warehouse, Store, Branch, etc.)."""
    if current_user.role.value not in ["admin", "superadmin", "owner", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permission to create locations")

    name = data.get("name")
    loc_type = data.get("type", "store")
    if not name:
        raise HTTPException(status_code=400, detail="Location name is required")

    loc = Location(
        organization_id=current_user.organization_id,
        name=name,
        code=data.get("code") or f"LOC-{loc_type.upper()[:3]}-{datetime.utcnow().strftime('%M%S')}",
        type=LocationType(loc_type) if loc_type in [t.value for t in LocationType] else LocationType.STORE,
        status=LocationStatus.ACTIVE,
        address=data.get("address", ""),
        city=data.get("city", ""),
        state=data.get("state"),
        postal_code=data.get("postal_code"),
        country=data.get("country", "Cameroon"),
        phone=data.get("phone"),
        email=data.get("email"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        manager_id=data.get("manager_id"),
        manager_name=data.get("manager_name"),
        is_central_hub=bool(data.get("is_central_hub", False)),
        allow_pos=bool(data.get("allow_pos", True))
    )
    await loc.insert()
    
    # If location is a WAREHOUSE, also sync with legacy Warehouse entity for compatibility
    if loc.type == LocationType.WAREHOUSE:
        wh = Warehouse(
            organization_id=current_user.organization_id,
            name=loc.name,
            code=loc.code or "WH",
            location_id=str(loc.id),
            phone=loc.phone,
            is_central_hub=loc.is_central_hub
        )
        await wh.insert()

    res = loc.model_dump()
    res["id"] = str(loc.id)
    return res


@router.get("/{location_id}/stock")
async def get_location_stock(
    location_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get detailed inventory breakdown for a specific location."""
    try:
        obj_id = PydanticObjectId(location_id)
        loc = await Location.find_one({"_id": obj_id, "organization_id": current_user.organization_id})
    except Exception:
        loc = None
        
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    stocks = await LocationStock.find({"location_id": location_id, "organization_id": current_user.organization_id}).to_list()
    
    # If location stocks are empty, seed location stocks from global product inventory
    if not stocks:
        products = await Product.find({"organization_id": current_user.organization_id}).to_list()
        new_stocks = []
        for p in products:
            p_stock = p.total_stock
            ls = LocationStock(
                organization_id=current_user.organization_id,
                location_id=location_id,
                product_id=str(p.id),
                sku=p.sku,
                product_name=p.name,
                on_hand=p_stock,
                available=max(0, p_stock - (p.reserved_stock or 0)),
                reserved=p.reserved_stock or 0,
                damaged=p.damaged_stock or 0,
                unit_cost=p.cost_price or 0.0
            )
            await ls.insert()
            new_stocks.append(ls)
        stocks = new_stocks

    result = []
    for s in stocks:
        d = s.model_dump()
        d["id"] = str(s.id)
        result.append(d)
        
    return result


@router.get("/{location_id}/terminals")
async def get_store_pos_terminals(
    location_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """List POS terminals attached to a Store location."""
    terminals = await POSTerminal.find({
        "store_id": location_id,
        "organization_id": current_user.organization_id
    }).to_list()
    
    # Auto-seed terminal if none exist for a store location
    if not terminals:
        t1 = POSTerminal(
            organization_id=current_user.organization_id,
            store_id=location_id,
            name="Main POS Terminal 01",
            code="POS-T01",
            status=POSTerminalStatus.ACTIVE
        )
        await t1.insert()
        terminals = [t1]

    result = []
    for t in terminals:
        d = t.model_dump()
        d["id"] = str(t.id)
        result.append(d)
    return result


@router.post("/{location_id}/terminals", status_code=status.HTTP_201_CREATED)
async def create_pos_terminal(
    location_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Create a new POS Terminal for a Store location."""
    name = data.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Terminal name is required")

    terminal = POSTerminal(
        organization_id=current_user.organization_id,
        store_id=location_id,
        name=name,
        code=data.get("code") or f"POS-{datetime.utcnow().strftime('%H%M%S')}",
        status=POSTerminalStatus.ACTIVE,
        assigned_cashier_id=data.get("assigned_cashier_id"),
        assigned_cashier_name=data.get("assigned_cashier_name")
    )
    await terminal.insert()
    
    d = terminal.model_dump()
    d["id"] = str(terminal.id)
    return d


@router.put("/{location_id}")
async def update_location(
    location_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Edit an existing location's details."""
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if current_user.user_type != "platform-staff" and role_val not in ["admin", "superadmin", "administrator", "owner", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permission to edit locations")

    loc = await Location.get(location_id)
    if not loc:
        try:
            loc = await Location.find_one({"_id": PydanticObjectId(location_id)})
        except Exception:
            pass

    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    if current_user.user_type != "platform-staff" and loc.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this location")

    # Allowed fields to update
    updatable = ["name", "code", "address", "city", "state", "postal_code", "country",
                 "phone", "email", "manager_id", "manager_name", "is_central_hub", "allow_pos", "type",
                 "latitude", "longitude"]
    for field in updatable:
        if field in data:
            if field == "type":
                try:
                    setattr(loc, field, LocationType(data[field]))
                except ValueError:
                    pass
            else:
                setattr(loc, field, data[field])

    loc.updated_at = datetime.utcnow()
    await loc.save()

    res = loc.model_dump()
    res["id"] = str(loc.id)
    return res


@router.patch("/{location_id}/status")
async def update_location_status(
    location_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Activate or deactivate a location."""
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if current_user.user_type != "platform-staff" and role_val not in ["admin", "superadmin", "administrator", "owner", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permission to change location status")

    loc = await Location.get(location_id)
    if not loc:
        try:
            loc = await Location.find_one({"_id": PydanticObjectId(location_id)})
        except Exception:
            pass

    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    new_status_str = data.get("status", "active")
    try:
        loc.status = LocationStatus(new_status_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status_str}")

    loc.updated_at = datetime.utcnow()
    await loc.save()

    res = loc.model_dump()
    res["id"] = str(loc.id)
    return res


@router.delete("/{location_id}")
async def delete_location(
    location_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Soft-delete a location by marking it inactive."""
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if current_user.user_type != "platform-staff" and role_val not in ["admin", "superadmin", "administrator", "owner"]:
        raise HTTPException(status_code=403, detail="Only administrators can delete locations")

    loc = await Location.get(location_id)
    if not loc:
        try:
            loc = await Location.find_one({"_id": PydanticObjectId(location_id)})
        except Exception:
            pass

    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    loc.status = LocationStatus.INACTIVE
    loc.updated_at = datetime.utcnow()
    await loc.save()

    return {"success": True, "id": location_id, "status": "inactive"}

