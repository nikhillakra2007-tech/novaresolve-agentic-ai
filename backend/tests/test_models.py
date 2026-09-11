import uuid
import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.db.models import (
    Customer,
    Product,
    Warehouse,
    Inventory,
    Order,
    OrderItem,
    Shipment,
    Policy,
    Case,
    Refund,
    Replacement,
    Cancellation,
    AgentEvent,
)


def test_customer_creation_and_constraints(db_session: Session):
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    customer = Customer(
        name="Test Constraint Customer",
        email=unique_email,
        phone="+1-555-0199",
        status="active",
    )
    db_session.add(customer)
    db_session.commit()
    assert customer.id is not None
    assert isinstance(customer.id, uuid.UUID)

    # Test invalid status constraint
    invalid_cust = Customer(
        name="Invalid Customer",
        email=f"invalid_{uuid.uuid4().hex[:8]}@example.com",
        status="non_existent_status",
    )
    db_session.add(invalid_cust)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_product_price_constraint(db_session: Session):
    invalid_prod = Product(
        sku=f"SKU-NEG-{uuid.uuid4().hex[:6]}",
        name="Negative Price Item",
        category="Test",
        price=Decimal("-10.00"),
    )
    db_session.add(invalid_prod)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_inventory_quantity_constraints(db_session: Session):
    warehouse = db_session.query(Warehouse).first()
    product = db_session.query(Product).first()

    # Reserved quantity exceeding total quantity must trigger check constraint
    inv_exceed = Inventory(
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity=5,
        reserved_quantity=10,  # invalid!
    )
    db_session.add(inv_exceed)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_order_cascade_delete_order_items(db_session: Session):
    customer = db_session.query(Customer).first()
    product = db_session.query(Product).first()

    # Create temporary order with item
    order = Order(
        customer_id=customer.id,
        status="placed",
        total_amount=Decimal("50.00"),
        shipping_address="123 Test Street",
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=2,
        unit_price=Decimal("25.00"),
    )
    db_session.add(item)
    db_session.commit()

    order_id = order.id
    item_id = item.id

    # Deleting order must cascade to order_items
    db_session.delete(order)
    db_session.commit()

    assert db_session.query(Order).filter(Order.id == order_id).first() is None
    assert db_session.query(OrderItem).filter(OrderItem.id == item_id).first() is None


def test_all_13_tables_registered_in_metadata():
    expected_tables = {
        "customers",
        "products",
        "warehouses",
        "inventory",
        "orders",
        "order_items",
        "shipments",
        "policies",
        "cases",
        "refunds",
        "replacements",
        "cancellations",
        "agent_events",
    }
    from backend.app.db.base import Base

    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"
