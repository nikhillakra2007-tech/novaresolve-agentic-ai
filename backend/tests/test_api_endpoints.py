import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.db.models import (
    Customer,
    Order,
    OrderItem,
    Product,
    Warehouse,
    Shipment,
)


def test_api_customer_endpoints(client: TestClient, db_session: Session):
    existing = db_session.query(Customer).filter(Customer.email == "scenario1_alice@example.com").first()
    assert existing is not None

    # GET /api/customers/{customer_id}
    res = client.get(f"/api/customers/{existing.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(existing.id)
    assert data["name"] == existing.name

    # GET /api/customers/by-email/{email}
    res_email = client.get(f"/api/customers/by-email/{existing.email}")
    assert res_email.status_code == 200
    assert res_email.json()["id"] == str(existing.id)

    # 404 cases
    res_404 = client.get(f"/api/customers/{uuid.uuid4()}")
    assert res_404.status_code == 404
    assert res_404.json()["error"] == "ResourceNotFoundError"

    res_email_404 = client.get("/api/customers/by-email/nobody_exists_here@example.com")
    assert res_email_404.status_code == 404


def test_api_order_endpoints(client: TestClient, db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario1_alice@example.com").first()
    order = db_session.query(Order).filter(Order.customer_id == customer.id).first()
    assert order is not None

    # GET /api/orders/{order_id}
    res = client.get(f"/api/orders/{order.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(order.id)
    assert len(data["items"]) > 0

    # With matching customer_id query param
    res_with_owner = client.get(f"/api/orders/{order.id}?customer_id={customer.id}")
    assert res_with_owner.status_code == 200

    # With mismatched customer_id query param
    res_mismatch = client.get(f"/api/orders/{order.id}?customer_id={uuid.uuid4()}")
    assert res_mismatch.status_code == 404


def test_api_shipment_endpoint(client: TestClient, db_session: Session):
    shipment = db_session.query(Shipment).first()
    assert shipment is not None

    res = client.get(f"/api/shipments/{shipment.order_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["order_id"] == str(shipment.order_id)
    assert "tracking_number" in data
    assert "is_delayed" in data

    # 404 when order has no shipment
    res_404 = client.get(f"/api/shipments/{uuid.uuid4()}")
    assert res_404.status_code == 404


def test_api_inventory_endpoints(client: TestClient, db_session: Session):
    dallas = db_session.query(Warehouse).filter(Warehouse.name == "Dallas Central Warehouse").first()
    product = db_session.query(Product).filter(Product.sku == "ELEC-4K-MONITOR-02").first()

    # Dallas has 0 stock for this product
    res = client.get(f"/api/inventory/{product.id}/{dallas.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["product_id"] == str(product.id)
    assert data["warehouse_id"] == str(dallas.id)
    assert data["quantity"] == 0
    assert data["available_quantity"] == 0

    # Alternatives discovery
    res_alt = client.get(f"/api/inventory/{product.id}/alternatives?required_quantity=1")
    assert res_alt.status_code == 200
    alt_data = res_alt.json()
    assert len(alt_data["alternatives"]) >= 1


def test_api_policy_evaluate(client: TestClient):
    payload = {
        "action_type": "refund",
        "amount": 25.50,
        "order_status": "delivered",
    }
    res = client.post("/api/policies/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["allowed"] is True
    assert data["requires_approval"] is False


def test_api_resolutions_refund(client: TestClient, db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario3_charlie@example.com").first()
    order = Order(
        customer_id=customer.id,
        total_amount=Decimal("150.00"),
        status="delivered",
        shipping_address="API Refund Address",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    # 1. Successful refund creation
    payload = {
        "order_id": str(order.id),
        "amount": 40.00,
        "reason": "Customer dissatisfied with color",
    }
    res = client.post("/api/refunds", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["order_id"] == str(order.id)
    assert data["status"] == "completed"

    # 2. Exceeding refund balance -> 400 Bad Request
    payload_excess = {
        "order_id": str(order.id),
        "amount": 200.00,
        "reason": "Excess claim",
    }
    res_excess = client.post("/api/refunds", json=payload_excess)
    assert res_excess.status_code == 400
    assert res_excess.json()["error"] == "BusinessRuleViolationError"


def test_api_resolutions_replacement_and_cancellation(client: TestClient, db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario2_bob@example.com").first()
    product = db_session.query(Product).filter(Product.sku == "ELEC-4K-MONITOR-02").first()
    dallas = db_session.query(Warehouse).filter(Warehouse.name == "Dallas Central Warehouse").first()

    order = Order(
        customer_id=customer.id,
        total_amount=Decimal("399.99"),
        status="delivered",
        shipping_address="Bob API Replacement Address",
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        unit_price=Decimal("399.99"),
    )
    db_session.add(item)
    db_session.commit()

    # Attempting replacement from Dallas (0 stock) -> 409 Conflict
    rep_payload = {
        "order_id": str(order.id),
        "product_id": str(product.id),
        "warehouse_id": str(dallas.id),
        "quantity": 1,
        "reason": "Broken screen",
    }
    res_rep = client.post("/api/replacements", json=rep_payload)
    assert res_rep.status_code == 409
    assert res_rep.json()["error"] == "InsufficientInventoryError"

    # Cancellation test on shipped order -> 409 Conflict
    scenario8_order = db_session.query(Order).join(Customer).filter(
        Customer.email == "scenario8_hannah@example.com"
    ).first()
    can_payload = {
        "order_id": str(scenario8_order.id),
        "reason": "Changed my mind",
    }
    res_can = client.post("/api/cancellations", json=can_payload)
    assert res_can.status_code == 409
    assert res_can.json()["error"] == "OrderStateConflictError"
