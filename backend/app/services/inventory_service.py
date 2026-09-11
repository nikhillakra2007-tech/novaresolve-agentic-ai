import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.app.db.models.inventory import Inventory
from backend.app.db.models.warehouse import Warehouse
from backend.app.db.models.product import Product
from backend.app.schemas.inventory import (
    InventoryResponse,
    AlternativeInventoryResponse,
    WarehouseInventoryOption,
)
from backend.app.core.exceptions import ResourceNotFoundError, BusinessRuleViolationError


class InventoryService:
    @staticmethod
    def check_inventory(
        db: Session,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> InventoryResponse:
        """Checks inventory for a specific product and warehouse without mutating or auto-rerouting."""
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ResourceNotFoundError(f"Product with ID '{product_id}' was not found.")

        warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
        if not warehouse:
            raise ResourceNotFoundError(f"Warehouse with ID '{warehouse_id}' was not found.")

        inventory = (
            db.query(Inventory)
            .filter(
                Inventory.product_id == product_id,
                Inventory.warehouse_id == warehouse_id,
            )
            .first()
        )

        quantity = inventory.quantity if inventory else 0
        reserved_quantity = inventory.reserved_quantity if inventory else 0
        available_quantity = max(0, quantity - reserved_quantity)
        updated_at = inventory.updated_at if inventory else product.created_at

        return InventoryResponse(
            warehouse_id=warehouse.id,
            warehouse_name=warehouse.name,
            warehouse_status=warehouse.status,
            product_id=product.id,
            product_sku=product.sku,
            product_name=product.name,
            quantity=quantity,
            reserved_quantity=reserved_quantity,
            available_quantity=available_quantity,
            updated_at=updated_at,
        )

    @staticmethod
    def search_alternative_inventory(
        db: Session,
        product_id: uuid.UUID,
        required_quantity: int = 1,
        exclude_warehouse_id: Optional[uuid.UUID] = None,
    ) -> AlternativeInventoryResponse:
        """Discovers alternative active warehouses with sufficient available inventory."""
        if required_quantity <= 0:
            raise BusinessRuleViolationError("Required quantity must be greater than zero.")

        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ResourceNotFoundError(f"Product with ID '{product_id}' was not found.")

        query = (
            db.query(Inventory, Warehouse)
            .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
            .filter(
                Inventory.product_id == product_id,
                Warehouse.status == "active",
                (Inventory.quantity - Inventory.reserved_quantity) >= required_quantity,
            )
        )

        if exclude_warehouse_id:
            query = query.filter(Inventory.warehouse_id != exclude_warehouse_id)

        results = query.all()
        alternatives = []
        for inv, wh in results:
            avail = max(0, inv.quantity - inv.reserved_quantity)
            alternatives.append(
                WarehouseInventoryOption(
                    warehouse_id=wh.id,
                    warehouse_name=wh.name,
                    location=wh.location,
                    warehouse_status=wh.status,
                    available_quantity=avail,
                )
            )

        return AlternativeInventoryResponse(
            product_id=product.id,
            product_sku=product.sku,
            required_quantity=required_quantity,
            alternatives=alternatives,
        )

    # Alias for uniform service interface
    find_alternative_warehouses = search_alternative_inventory
