import uuid
import pytest
from sqlalchemy.orm import Session

from backend.app.core.exceptions import ResourceNotFoundError
from backend.app.db.models import Customer, Order, Warehouse, Product
from backend.app.services.customer_service import CustomerService
from backend.app.services.order_service import OrderService
from backend.app.services.shipment_service import ShipmentService
from backend.app.services.inventory_service import InventoryService


def test_customer_service_get_by_id_and_email(db_session: Session):
    existing = db_session.query(Customer).filter(Customer.email == "scenario1_alice@example.com").first()
    assert existing is not None

    by_id = CustomerService.get_customer_by_id(db_session, existing.id)
    assert by_id.id == existing.id
    assert by_id.name == existing.name

    by_email = CustomerService.get_customer_by_email(db_session, "Scenario1_Alice@example.COM ")
    assert by_email.id == existing.id


def test_customer_service_not_found(db_session: Session):
    random_id = uuid.uuid4()
    with pytest.raises(ResourceNotFoundError) as exc_info:
        CustomerService.get_customer_by_id(db_session, random_id)
    assert str(random_id) in str(exc_info.value)

    with pytest.raises(ResourceNotFoundError):
        CustomerService.get_customer_by_email(db_session, "non_existent_customer_xyz@example.com")


def test_order_service_get_order_with_items(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario1_alice@example.com").first()
    order = db_session.query(Order).filter(Order.customer_id == customer.id).first()
    assert order is not None

    fetched = OrderService.get_order(db_session, order.id)
    assert fetched.id == order.id
    assert len(fetched.items) > 0

    # With matching customer_id
    verified = OrderService.get_order(db_session, order.id, customer_id=customer.id)
    assert verified.id == order.id

    # With mismatched customer_id
    random_customer_id = uuid.uuid4()
    with pytest.raises(ResourceNotFoundError):
        OrderService.get_order(db_session, order.id, customer_id=random_customer_id)


def test_shipment_service_tracking_and_delay(db_session: Session):
    # Scenario 5 order is delayed
    customer = db_session.query(Customer).filter(Customer.email == "scenario5_evan@example.com").first()
    order = db_session.query(Order).filter(Order.customer_id == customer.id).first()
    assert order is not None

    shipment = ShipmentService.get_shipment_by_order_id(db_session, order.id)
    assert shipment is not None
    assert shipment.status == "delayed"
    assert shipment.is_delayed is True
    assert shipment.carrier in ["FedEx", "UPS", "USPS", "DHL"]


def test_inventory_service_observable_zero_stock(db_session: Session):
    # Scenario 2 has Dallas monitor with quantity = 0
    dallas = db_session.query(Warehouse).filter(Warehouse.name == "Dallas Central Warehouse").first()
    product = db_session.query(Product).filter(Product.sku == "ELEC-4K-MONITOR-02").first()

    inv = InventoryService.check_inventory(db_session, product.id, dallas.id)
    assert inv.product_id == product.id
    assert inv.warehouse_id == dallas.id
    assert inv.quantity == 0
    assert inv.available_quantity == 0


def test_inventory_service_find_alternatives(db_session: Session):
    product = db_session.query(Product).filter(Product.sku == "ELEC-4K-MONITOR-02").first()
    alternatives = InventoryService.find_alternative_warehouses(db_session, product.id, required_quantity=1)

    assert alternatives.product_id == product.id
    assert alternatives.required_quantity == 1
    assert len(alternatives.alternatives) >= 1

    # Reno must be present as an alternative
    reno_option = next(
        (w for w in alternatives.alternatives if "Reno" in w.warehouse_name),
        None,
    )
    assert reno_option is not None
    assert reno_option.available_quantity >= 1
