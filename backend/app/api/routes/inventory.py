from uuid import UUID
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.inventory import (
    InventoryResponse,
    AlternativeInventoryResponse,
)
from backend.app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get(
    "/{product_id}/alternatives",
    response_model=AlternativeInventoryResponse,
    summary="Find Alternative Warehouses with Stock",
    description=(
        "Discovers active warehouses that currently have sufficient available quantity "
        "(quantity - reserved_quantity >= required_quantity) for a specific product."
    ),
)
def find_alternative_warehouses(
    product_id: UUID = Path(..., description="Unique product UUID"),
    required_quantity: int = Query(1, ge=1, description="Minimum quantity needed"),
    db: Session = Depends(get_db),
):
    alternatives = InventoryService.find_alternative_warehouses(
        db, product_id=product_id, required_quantity=required_quantity
    )
    return alternatives


@router.get(
    "/{product_id}/{warehouse_id}",
    response_model=InventoryResponse,
    summary="Check Specific Warehouse Inventory",
    description=(
        "Returns the exact quantity and reserved quantity for a product in a warehouse. "
        "Preserves zero-stock observation (does not fail or auto-reroute)."
    ),
)
def check_inventory(
    product_id: UUID = Path(..., description="Unique product UUID"),
    warehouse_id: UUID = Path(..., description="Unique warehouse UUID"),
    db: Session = Depends(get_db),
):
    inventory = InventoryService.check_inventory(
        db, product_id=product_id, warehouse_id=warehouse_id
    )
    return inventory
