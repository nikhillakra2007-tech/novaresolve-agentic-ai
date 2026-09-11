"""NovaCart Synthetic Seed Data Generator.

Deterministic seeding of:
- 4 Warehouses
- 26 Products
- 60 Customers (10 Scenario Customers + 50 Synthetic Customers)
- Realistic Inventory Matrix (including scenario-specific stock levels)
- 220+ Orders and Order Items
- 180+ Shipments with tracking numbers and carriers
- 6 Resolution Policies with JSONB conditions
- Pre-seeded Cases, Agent Events, Refunds, Replacements, and Cancellations for Scenarios
"""

import uuid
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Tuple

from sqlalchemy.orm import Session
from backend.app.db.session import SessionLocal, engine
from backend.app.db.base import Base
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
from db.seed.scenarios import SCENARIOS

# Seed random for deterministic runs
random.seed(42)

NOW = datetime.now(timezone.utc)


def seed_warehouses(db: Session) -> Dict[str, Warehouse]:
    warehouses_data = [
        {"name": "Dallas Central Warehouse", "location": "Dallas, TX", "status": "active"},
        {"name": "Atlanta East Warehouse", "location": "Atlanta, GA", "status": "active"},
        {"name": "Reno West Warehouse", "location": "Reno, NV", "status": "active"},
        {"name": "Chicago North Warehouse", "location": "Chicago, IL", "status": "active"},
    ]
    warehouse_map: Dict[str, Warehouse] = {}
    for w_data in warehouses_data:
        warehouse = Warehouse(
            name=w_data["name"],
            location=w_data["location"],
            status=w_data["status"],
        )
        db.add(warehouse)
        warehouse_map[w_data["name"]] = warehouse

    db.flush()
    return warehouse_map


def seed_products(db: Session) -> Dict[str, Product]:
    products_data = [
        # Scenario specific products
        {"sku": "AUD-NC-HEADPHONES-01", "name": "NovaSound Active Noise Cancelling Headphones", "category": "Audio", "price": Decimal("149.99")},
        {"sku": "ELEC-4K-MONITOR-02", "name": "NovaView 27-inch 4K UHD Monitor", "category": "Electronics", "price": Decimal("329.50")},
        {"sku": "ACC-USB-C-DOCK-03", "name": "NovaConnect 8-in-1 USB-C Hub", "category": "Accessories", "price": Decimal("45.00")},
        {"sku": "ELEC-SMART-PROJ-04", "name": "NovaBeam Pro Smart Laser Projector", "category": "Electronics", "price": Decimal("520.00")},
        {"sku": "ELEC-TABLET-10INCH-05", "name": "NovaTab 10 Pro 128GB", "category": "Electronics", "price": Decimal("249.00")},
        {"sku": "HOME-AIR-PURIFIER-06", "name": "NovaPure HEPA Air Purifier 300", "category": "Home", "price": Decimal("89.99")},
        {"sku": "WEAR-SMARTWATCH-07", "name": "NovaFit Pulse GPS Smartwatch", "category": "Wearables", "price": Decimal("129.95")},
        {"sku": "AUD-BT-SPEAKER-08", "name": "NovaBoom Rugged Bluetooth Speaker", "category": "Audio", "price": Decimal("59.99")},
        {"sku": "ACC-WIRELESS-CHARGER-09", "name": "NovaCharge Fast Qi Wireless Pad", "category": "Accessories", "price": Decimal("29.99")},
        {"sku": "HOME-ROBOT-VAC-10", "name": "NovaClean Lidar Robot Vacuum", "category": "Home", "price": Decimal("399.00")},

        # General catalog products
        {"sku": "ELEC-MECH-KEYBOARD-11", "name": "NovaKey RGB Mechanical Keyboard", "category": "Electronics", "price": Decimal("79.99")},
        {"sku": "ACC-ERGONOMIC-MOUSE-12", "name": "NovaGlide Ergonomic Wireless Mouse", "category": "Accessories", "price": Decimal("39.99")},
        {"sku": "AUD-TRUE-WIRELESS-13", "name": "NovaBuds Pro Wireless Earbuds", "category": "Audio", "price": Decimal("89.00")},
        {"sku": "HOME-LED-DESK-LAMP-14", "name": "NovaGlow Smart LED Desk Lamp", "category": "Home", "price": Decimal("34.50")},
        {"sku": "WEAR-FIT-BAND-15", "name": "NovaBand Slim Fitness Tracker", "category": "Wearables", "price": Decimal("49.99")},
        {"sku": "ELEC-USB-MICROPHONE-16", "name": "NovaMic Studio USB Condenser Mic", "category": "Audio", "price": Decimal("69.99")},
        {"sku": "ACC-LAPTOP-STAND-17", "name": "NovaStand Aluminum Laptop Riser", "category": "Accessories", "price": Decimal("24.99")},
        {"sku": "HOME-COFFEE-MAKER-18", "name": "NovaBrew Thermal Programmable Brewer", "category": "Home", "price": Decimal("64.99")},
        {"sku": "HOME-SMART-PLUG-19", "name": "NovaPlug Wi-Fi Smart Power Outlet", "category": "Home", "price": Decimal("18.99")},
        {"sku": "WEAR-OPEN-EAR-20", "name": "NovaAir Bone Conduction Sport Headset", "category": "Wearables", "price": Decimal("99.95")},
        {"sku": "ELEC-EXTERNAL-SSD-21", "name": "NovaSpeed 1TB Portable NVMe SSD", "category": "Electronics", "price": Decimal("109.99")},
        {"sku": "ACC-GAN-CHARGER-22", "name": "NovaVolt 65W Dual GaN Wall Charger", "category": "Accessories", "price": Decimal("35.00")},
        {"sku": "HOME-BLENDER-PRO-23", "name": "NovaMix High-Speed Pulse Blender", "category": "Home", "price": Decimal("79.00")},
        {"sku": "AUD-GAMING-HEADSET-24", "name": "NovaStrike 7.1 Surround Gaming Headset", "category": "Audio", "price": Decimal("69.50")},
        {"sku": "ELEC-WEBCAM-4K-25", "name": "NovaCam 4K HDR Autofocus Webcam", "category": "Electronics", "price": Decimal("89.99")},
        {"sku": "HOME-HUMIDIFIER-26", "name": "NovaMist Ultrasonic Cool Humidifier", "category": "Home", "price": Decimal("42.00")},
    ]

    product_map: Dict[str, Product] = {}
    for p_data in products_data:
        product = Product(
            sku=p_data["sku"],
            name=p_data["name"],
            category=p_data["category"],
            price=p_data["price"],
            active=True,
        )
        db.add(product)
        product_map[p_data["sku"]] = product

    db.flush()
    return product_map


def seed_inventory(
    db: Session,
    warehouses: Dict[str, Warehouse],
    products: Dict[str, Product],
) -> List[Inventory]:
    inventories: List[Inventory] = []
    dallas = warehouses["Dallas Central Warehouse"]
    atlanta = warehouses["Atlanta East Warehouse"]
    reno = warehouses["Reno West Warehouse"]
    chicago = warehouses["Chicago North Warehouse"]

    for sku, product in products.items():
        if sku == "ELEC-4K-MONITOR-02":
            # Scenario 2 constraint: Zero stock in Dallas primary, ample stock in Reno alternate
            inv_dallas = Inventory(warehouse_id=dallas.id, product_id=product.id, quantity=0, reserved_quantity=0)
            inv_reno = Inventory(warehouse_id=reno.id, product_id=product.id, quantity=15, reserved_quantity=2)
            inv_atlanta = Inventory(warehouse_id=atlanta.id, product_id=product.id, quantity=0, reserved_quantity=0)
            inv_chicago = Inventory(warehouse_id=chicago.id, product_id=product.id, quantity=0, reserved_quantity=0)
            db.add_all([inv_dallas, inv_reno, inv_atlanta, inv_chicago])
            inventories.extend([inv_dallas, inv_reno, inv_atlanta, inv_chicago])
        elif sku == "AUD-NC-HEADPHONES-01":
            # Scenario 1 constraint: Ample stock in Dallas primary
            inv_dallas = Inventory(warehouse_id=dallas.id, product_id=product.id, quantity=45, reserved_quantity=3)
            inv_reno = Inventory(warehouse_id=reno.id, product_id=product.id, quantity=20, reserved_quantity=1)
            inv_atlanta = Inventory(warehouse_id=atlanta.id, product_id=product.id, quantity=25, reserved_quantity=0)
            inv_chicago = Inventory(warehouse_id=chicago.id, product_id=product.id, quantity=30, reserved_quantity=2)
            db.add_all([inv_dallas, inv_reno, inv_atlanta, inv_chicago])
            inventories.extend([inv_dallas, inv_reno, inv_atlanta, inv_chicago])
        else:
            # Realistic general distribution
            for w in [dallas, atlanta, reno, chicago]:
                qty = random.randint(10, 80)
                res = random.randint(0, min(5, qty))
                inv = Inventory(
                    warehouse_id=w.id,
                    product_id=product.id,
                    quantity=qty,
                    reserved_quantity=res,
                )
                db.add(inv)
                inventories.append(inv)

    db.flush()
    return inventories


def seed_customers(db: Session) -> Tuple[Dict[str, Customer], List[Customer]]:
    scenario_customers_data = [
        ("scenario1_alice@example.com", "Alice Walker", "+1-214-555-0101", "active"),
        ("scenario2_bob@example.com", "Bob Martinez", "+1-415-555-0102", "active"),
        ("scenario3_charlie@example.com", "Charlie Davis", "+1-206-555-0103", "active"),
        ("scenario4_diana@example.com", "Diana Prince", "+1-312-555-0104", "active"),
        ("scenario5_evan@example.com", "Evan Wright", "+1-404-555-0105", "active"),
        ("scenario6_fiona@example.com", "Fiona Gallagher", "+1-617-555-0106", "active"),
        ("scenario7_george@example.com", "George Clark", "+1-713-555-0107", "active"),
        ("scenario8_hannah@example.com", "Hannah Abbott", "+1-303-555-0108", "active"),
        ("scenario9_ian@example.com", "Ian Malcolm", "+1-503-555-0109", "active"),
        ("scenario10_julia@example.com", "Julia Roberts", "+1-619-555-0110", "active"),
    ]

    scenario_map: Dict[str, Customer] = {}
    all_customers: List[Customer] = []

    for email, name, phone, status in scenario_customers_data:
        cust = Customer(name=name, email=email, phone=phone, status=status)
        db.add(cust)
        scenario_map[email] = cust
        all_customers.append(cust)

    # 50 general synthetic customers (total 60)
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth",
                   "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                  "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]

    for i in range(1, 51):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        email = f"customer_{i}_{name.lower().replace(' ', '.')}@example.com"
        phone = f"+1-{random.randint(200, 999)}-555-{random.randint(1000, 9999)}"
        status = "blocked" if i == 13 else ("inactive" if i == 27 else "active")
        cust = Customer(name=name, email=email, phone=phone, status=status)
        db.add(cust)
        all_customers.append(cust)

    db.flush()
    return scenario_map, all_customers


def seed_policies(db: Session) -> List[Policy]:
    policies_data = [
        {
            "issue_type": "refund",
            "action": "auto_refund",
            "conditions": {
                "max_amount": 100.0,
                "within_days": 30,
                "requires_delivery": True,
                "allowed_reasons": ["damaged", "wrong_item", "defective", "not_as_described"],
            },
            "risk_level": "low",
            "priority": 10,
        },
        {
            "issue_type": "refund",
            "action": "supervisor_approval_required",
            "conditions": {
                "min_amount": 100.0,
                "within_days": 30,
                "requires_human_review": True,
            },
            "risk_level": "high",
            "priority": 20,
        },
        {
            "issue_type": "replacement",
            "action": "create_replacement_order",
            "conditions": {
                "within_days": 45,
                "requires_inventory_check": True,
                "allow_alternate_warehouse": True,
                "auto_approve_tier": "standard",
            },
            "risk_level": "low",
            "priority": 15,
        },
        {
            "issue_type": "cancellation",
            "action": "cancel_unshipped_order",
            "conditions": {
                "allowed_order_statuses": ["placed", "processing"],
                "disallowed_order_statuses": ["shipped", "delivered", "cancelled"],
                "auto_void_payment": True,
            },
            "risk_level": "low",
            "priority": 5,
        },
        {
            "issue_type": "delay",
            "action": "carrier_investigation_and_replan",
            "conditions": {
                "delayed_days_threshold": 3,
                "expedited_replacement_eligible": True,
                "courtesy_credit_amount": 15.0,
            },
            "risk_level": "medium",
            "priority": 25,
        },
        {
            "issue_type": "damage",
            "action": "damage_resolution_protocol",
            "conditions": {
                "requires_photo_reference": True,
                "return_label_required": False,
                "choice_allowed": ["replacement", "refund"],
            },
            "risk_level": "medium",
            "priority": 30,
        },
    ]

    policies: List[Policy] = []
    for pol in policies_data:
        p = Policy(
            issue_type=pol["issue_type"],
            action=pol["action"],
            conditions=pol["conditions"],
            risk_level=pol["risk_level"],
            active=True,
            priority=pol["priority"],
        )
        db.add(p)
        policies.append(p)

    db.flush()
    return policies


def seed_orders_and_scenarios(
    db: Session,
    scenario_customers: Dict[str, Customer],
    all_customers: List[Customer],
    products: Dict[str, Product],
    warehouses: Dict[str, Warehouse],
) -> int:
    carriers = ["FedEx", "UPS", "DHL Express", "USPS"]
    dallas = warehouses["Dallas Central Warehouse"]
    reno = warehouses["Reno West Warehouse"]
    total_order_count = 0

    # -------------------------------------------------------------
    # SCENARIO 1: Replacement succeeds normally
    # -------------------------------------------------------------
    c1 = scenario_customers["scenario1_alice@example.com"]
    p1 = products["AUD-NC-HEADPHONES-01"]
    o1 = Order(
        customer_id=c1.id,
        status="delivered",
        total_amount=p1.price,
        order_date=NOW - timedelta(days=7),
        expected_delivery=NOW - timedelta(days=4),
        actual_delivery=NOW - timedelta(days=4),
        shipping_address="742 Evergreen Terrace, Dallas, TX 75201",
    )
    db.add(o1)
    db.flush()
    total_order_count += 1

    oi1 = OrderItem(order_id=o1.id, product_id=p1.id, quantity=1, unit_price=p1.price)
    sh1 = Shipment(
        order_id=o1.id,
        tracking_number="TRK-SCENARIO1-FDX-1001",
        carrier="FedEx",
        status="delivered",
        shipped_at=NOW - timedelta(days=6),
        estimated_delivery=NOW - timedelta(days=4),
        actual_delivery=NOW - timedelta(days=4),
    )
    case1 = Case(
        customer_id=c1.id,
        order_id=o1.id,
        issue_type="defective_product",
        customer_goal="Customer received headphones with distorted right audio channel; desires direct replacement.",
        status="verifying",
        risk_level="low",
        current_plan=["verify_order", "check_policy", "check_inventory", "create_replacement", "verify_resolution"],
        current_step="verify_resolution",
        resolution_type="replacement",
        resolution_status="in_progress",
        requires_approval=False,
    )
    db.add_all([oi1, sh1, case1])
    db.flush()

    rep1 = Replacement(
        order_id=o1.id,
        case_id=case1.id,
        product_id=p1.id,
        warehouse_id=dallas.id,
        reason="Right audio driver distortion - replaced under standard warranty",
        status="processing",
        requires_approval=False,
    )
    evt1_1 = AgentEvent(
        case_id=case1.id,
        event_type="CASE_CREATED",
        tool_name="init_case",
        input_data={"order_id": str(o1.id), "issue": "distorted audio"},
        output_data={"case_id": str(case1.id), "risk_level": "low"},
        status="success",
        message="Case initiated for defective headphones replacement",
    )
    evt1_2 = AgentEvent(
        case_id=case1.id,
        event_type="INVENTORY_CHECK",
        tool_name="check_inventory",
        input_data={"warehouse_id": str(dallas.id), "sku": p1.sku},
        output_data={"available": 45, "status": "in_stock"},
        status="success",
        message="Primary Dallas warehouse has 45 units available.",
    )
    db.add_all([rep1, evt1_1, evt1_2])

    # -------------------------------------------------------------
    # SCENARIO 2: Replacement fails at primary warehouse, alternate warehouse stock exists
    # -------------------------------------------------------------
    c2 = scenario_customers["scenario2_bob@example.com"]
    p2 = products["ELEC-4K-MONITOR-02"]
    o2 = Order(
        customer_id=c2.id,
        status="delivered",
        total_amount=p2.price,
        order_date=NOW - timedelta(days=12),
        expected_delivery=NOW - timedelta(days=8),
        actual_delivery=NOW - timedelta(days=8),
        shipping_address="500 Market Street, San Francisco, CA 94105",
    )
    db.add(o2)
    db.flush()
    total_order_count += 1

    oi2 = OrderItem(order_id=o2.id, product_id=p2.id, quantity=1, unit_price=p2.price)
    sh2 = Shipment(
        order_id=o2.id,
        tracking_number="TRK-SCENARIO2-UPS-2002",
        carrier="UPS",
        status="delivered",
        shipped_at=NOW - timedelta(days=10),
        estimated_delivery=NOW - timedelta(days=8),
        actual_delivery=NOW - timedelta(days=8),
    )
    case2 = Case(
        customer_id=c2.id,
        order_id=o2.id,
        issue_type="replacement_out_of_stock",
        customer_goal="Monitor panel has vertical line defect. Needs replacement. Dallas warehouse is out of stock.",
        status="replanning",
        risk_level="medium",
        current_plan=["verify_order", "check_inventory_primary", "detect_constraint", "search_alternative_inventory", "reroute_replacement"],
        current_step="search_alternative_inventory",
        resolution_type="replacement",
        resolution_status="replanning_alternate_hub",
        requires_approval=False,
    )
    db.add_all([oi2, sh2, case2])
    db.flush()

    evt2_1 = AgentEvent(
        case_id=case2.id,
        event_type="INVENTORY_CHECK",
        tool_name="check_inventory",
        input_data={"warehouse": "Dallas Central Warehouse", "sku": p2.sku},
        output_data={"quantity": 0},
        status="constraint",
        message="Primary warehouse Dallas has 0 quantity available.",
    )
    evt2_2 = AgentEvent(
        case_id=case2.id,
        event_type="CONSTRAINT_DETECTED",
        tool_name="eval_inventory_constraint",
        input_data={"sku": p2.sku, "target_warehouse": str(dallas.id)},
        output_data={"action": "replan_required"},
        status="detected",
        message="Primary warehouse stockout. Agent triggering replan to search alternate warehouses.",
    )
    evt2_3 = AgentEvent(
        case_id=case2.id,
        event_type="REPLAN_STARTED",
        tool_name="search_alternative_inventory",
        input_data={"sku": p2.sku},
        output_data={"alternate_warehouse": "Reno West Warehouse", "quantity": 15},
        status="in_progress",
        message="Alternative warehouse Reno West located with 15 units.",
    )
    db.add_all([evt2_1, evt2_2, evt2_3])

    # -------------------------------------------------------------
    # SCENARIO 3: Refund below approval threshold (< $100) -> Auto approved
    # -------------------------------------------------------------
    c3 = scenario_customers["scenario3_charlie@example.com"]
    p3 = products["ACC-USB-C-DOCK-03"]  # $45.00
    o3 = Order(
        customer_id=c3.id,
        status="delivered",
        total_amount=p3.price,
        order_date=NOW - timedelta(days=5),
        expected_delivery=NOW - timedelta(days=2),
        actual_delivery=NOW - timedelta(days=2),
        shipping_address="1200 Pine Street, Seattle, WA 98101",
    )
    db.add(o3)
    db.flush()
    total_order_count += 1

    oi3 = OrderItem(order_id=o3.id, product_id=p3.id, quantity=1, unit_price=p3.price)
    sh3 = Shipment(
        order_id=o3.id,
        tracking_number="TRK-SCENARIO3-USPS-3003",
        carrier="USPS",
        status="delivered",
        shipped_at=NOW - timedelta(days=4),
        estimated_delivery=NOW - timedelta(days=2),
        actual_delivery=NOW - timedelta(days=2),
    )
    case3 = Case(
        customer_id=c3.id,
        order_id=o3.id,
        issue_type="damaged_accessory",
        customer_goal="USB-C dock ports loose on arrival; customer requested full refund ($45.00).",
        status="resolved",
        risk_level="low",
        current_plan=["verify_order", "check_refund_policy", "execute_refund", "verify_refund"],
        current_step="completed",
        resolution_type="refund",
        resolution_status="completed",
        requires_approval=False,
    )
    db.add_all([oi3, sh3, case3])
    db.flush()

    ref3 = Refund(
        order_id=o3.id,
        case_id=case3.id,
        amount=Decimal("45.00"),
        reason="Damaged HDMI connector on USB dock - auto-approved under $100 threshold",
        status="completed",
        requires_approval=False,
        approved_by="agent_auto_policy",
        processed_at=NOW - timedelta(hours=1),
    )
    evt3 = AgentEvent(
        case_id=case3.id,
        event_type="ACTION_EXECUTED",
        tool_name="create_refund",
        input_data={"amount": 45.00, "threshold": 100.00},
        output_data={"refund_id": str(ref3.id), "status": "completed"},
        status="success",
        message="Refund of $45.00 automatically processed below approval threshold.",
    )
    db.add_all([ref3, evt3])

    # -------------------------------------------------------------
    # SCENARIO 4: Refund exceeds approval threshold (>= $100) -> High risk, approval required
    # -------------------------------------------------------------
    c4 = scenario_customers["scenario4_diana@example.com"]
    p4 = products["ELEC-SMART-PROJ-04"]  # $520.00
    o4 = Order(
        customer_id=c4.id,
        status="delivered",
        total_amount=p4.price,
        order_date=NOW - timedelta(days=4),
        expected_delivery=NOW - timedelta(days=1),
        actual_delivery=NOW - timedelta(days=1),
        shipping_address="333 Michigan Ave, Chicago, IL 60601",
    )
    db.add(o4)
    db.flush()
    total_order_count += 1

    oi4 = OrderItem(order_id=o4.id, product_id=p4.id, quantity=1, unit_price=p4.price)
    sh4 = Shipment(
        order_id=o4.id,
        tracking_number="TRK-SCENARIO4-FDX-4004",
        carrier="FedEx",
        status="delivered",
        shipped_at=NOW - timedelta(days=3),
        estimated_delivery=NOW - timedelta(days=1),
        actual_delivery=NOW - timedelta(days=1),
    )
    case4 = Case(
        customer_id=c4.id,
        order_id=o4.id,
        issue_type="high_value_refund",
        customer_goal="Customer returning $520 projector. System must halt and require supervisor approval.",
        status="awaiting_approval",
        risk_level="high",
        current_plan=["verify_order", "check_policy_threshold", "trigger_approval_workflow", "await_supervisor"],
        current_step="trigger_approval_workflow",
        resolution_type="refund",
        resolution_status="pending_human_approval",
        requires_approval=True,
    )
    db.add_all([oi4, sh4, case4])
    db.flush()

    ref4 = Refund(
        order_id=o4.id,
        case_id=case4.id,
        amount=Decimal("520.00"),
        reason="Projector optical unit dead on arrival. Requires managerial sign-off (> $100).",
        status="pending",
        requires_approval=True,
        approved_by=None,
    )
    evt4 = AgentEvent(
        case_id=case4.id,
        event_type="APPROVAL_REQUIRED",
        tool_name="check_policy",
        input_data={"amount": 520.00, "threshold": 100.00},
        output_data={"requires_approval": True, "risk_level": "high"},
        status="pending",
        message="Amount $520.00 exceeds autonomous refund threshold ($100). Flagged for supervisor approval.",
    )
    db.add_all([ref4, evt4])

    # -------------------------------------------------------------
    # SCENARIO 5: Order delayed in transit
    # -------------------------------------------------------------
    c5 = scenario_customers["scenario5_evan@example.com"]
    p5 = products["WEAR-SMARTWATCH-07"]
    o5 = Order(
        customer_id=c5.id,
        status="shipped",
        total_amount=p5.price,
        order_date=NOW - timedelta(days=9),
        expected_delivery=NOW - timedelta(days=4),  # 4 days overdue
        shipping_address="88 Peachtree St NE, Atlanta, GA 30303",
    )
    db.add(o5)
    db.flush()
    total_order_count += 1

    oi5 = OrderItem(order_id=o5.id, product_id=p5.id, quantity=1, unit_price=p5.price)
    sh5 = Shipment(
        order_id=o5.id,
        tracking_number="TRK-SCENARIO5-UPS-5005",
        carrier="UPS",
        status="delayed",
        shipped_at=NOW - timedelta(days=8),
        estimated_delivery=NOW - timedelta(days=4),
    )
    case5 = Case(
        customer_id=c5.id,
        order_id=o5.id,
        issue_type="delayed_order",
        customer_goal="Order is 4 days past expected delivery date. Tracking shows severe weather delay in hub.",
        status="investigating",
        risk_level="medium",
        current_plan=["lookup_carrier_status", "evaluate_delay_threshold", "offer_courtesy_credit_or_reship"],
        current_step="evaluate_delay_threshold",
        resolution_type="delay_compensation",
        resolution_status="carrier_trace_in_progress",
        requires_approval=False,
    )
    db.add_all([oi5, sh5, case5])
    db.flush()

    evt5 = AgentEvent(
        case_id=case5.id,
        event_type="SHIPMENT_LOOKUP",
        tool_name="get_shipment",
        input_data={"tracking_number": "TRK-SCENARIO5-UPS-5005"},
        output_data={"status": "delayed", "days_overdue": 4},
        status="success",
        message="Carrier confirms severe delay. Overdue threshold met.",
    )
    db.add(evt5)

    # -------------------------------------------------------------
    # SCENARIO 6: Order delivered but customer reports damage
    # -------------------------------------------------------------
    c6 = scenario_customers["scenario6_fiona@example.com"]
    p6 = products["ELEC-TABLET-10INCH-05"]
    o6 = Order(
        customer_id=c6.id,
        status="delivered",
        total_amount=p6.price,
        order_date=NOW - timedelta(days=3),
        expected_delivery=NOW - timedelta(days=1),
        actual_delivery=NOW - timedelta(days=1),
        shipping_address="100 Boylston St, Boston, MA 02116",
    )
    db.add(o6)
    db.flush()
    total_order_count += 1

    oi6 = OrderItem(order_id=o6.id, product_id=p6.id, quantity=1, unit_price=p6.price)
    sh6 = Shipment(
        order_id=o6.id,
        tracking_number="TRK-SCENARIO6-DHL-6006",
        carrier="DHL Express",
        status="delivered",
        shipped_at=NOW - timedelta(days=2),
        estimated_delivery=NOW - timedelta(days=1),
        actual_delivery=NOW - timedelta(days=1),
    )
    case6 = Case(
        customer_id=c6.id,
        order_id=o6.id,
        issue_type="damaged_in_transit",
        customer_goal="Tablet screen cracked during shipping. Customer provided photo reference; desires rapid replacement.",
        status="planning",
        risk_level="low",
        current_plan=["verify_delivery", "validate_damage_claim", "check_inventory", "create_replacement"],
        current_step="validate_damage_claim",
        resolution_type="replacement",
        resolution_status="claim_validated",
        requires_approval=False,
    )
    db.add_all([oi6, sh6, case6])
    db.flush()

    evt6 = AgentEvent(
        case_id=case6.id,
        event_type="POLICY_CHECK",
        tool_name="check_policy",
        input_data={"issue_type": "damage", "evidence": "photo_submitted"},
        output_data={"action": "expedited_replacement", "return_required": False},
        status="success",
        message="Damage policy check satisfied. Direct replacement authorized.",
    )
    db.add(evt6)

    # -------------------------------------------------------------
    # SCENARIO 7: Cancellation is allowed (order status 'placed', no shipment)
    # -------------------------------------------------------------
    c7 = scenario_customers["scenario7_george@example.com"]
    p7 = products["HOME-AIR-PURIFIER-06"]
    o7 = Order(
        customer_id=c7.id,
        status="placed",
        total_amount=p7.price,
        order_date=NOW - timedelta(minutes=45),
        expected_delivery=NOW + timedelta(days=3),
        shipping_address="4520 Westheimer Rd, Houston, TX 77027",
    )
    db.add(o7)
    db.flush()
    total_order_count += 1

    oi7 = OrderItem(order_id=o7.id, product_id=p7.id, quantity=1, unit_price=p7.price)
    case7 = Case(
        customer_id=c7.id,
        order_id=o7.id,
        issue_type="order_cancellation",
        customer_goal="Customer ordered wrong model 45 minutes ago. Wants immediate cancellation and refund.",
        status="executing",
        risk_level="low",
        current_plan=["check_order_status", "verify_cancellation_policy", "cancel_order", "verify_cancellation"],
        current_step="cancel_order",
        resolution_type="cancellation",
        resolution_status="cancellation_permitted",
        requires_approval=False,
    )
    db.add_all([oi7, case7])
    db.flush()

    canc7 = Cancellation(
        order_id=o7.id,
        case_id=case7.id,
        reason="Customer requested cancellation before shipment fulfillment",
        status="approved",
        requires_approval=False,
    )
    evt7 = AgentEvent(
        case_id=case7.id,
        event_type="POLICY_CHECK",
        tool_name="check_policy",
        input_data={"order_status": "placed", "minutes_since_order": 45},
        output_data={"can_cancel": True},
        status="success",
        message="Order is unshipped. Direct cancellation allowed by policy.",
    )
    db.add_all([canc7, evt7])

    # -------------------------------------------------------------
    # SCENARIO 8: Cancellation blocked because order shipped
    # -------------------------------------------------------------
    c8 = scenario_customers["scenario8_hannah@example.com"]
    p8 = products["AUD-BT-SPEAKER-08"]
    o8 = Order(
        customer_id=c8.id,
        status="shipped",
        total_amount=p8.price,
        order_date=NOW - timedelta(days=2),
        expected_delivery=NOW + timedelta(days=1),
        shipping_address="1440 16th St, Denver, CO 80202",
    )
    db.add(o8)
    db.flush()
    total_order_count += 1

    oi8 = OrderItem(order_id=o8.id, product_id=p8.id, quantity=1, unit_price=p8.price)
    sh8 = Shipment(
        order_id=o8.id,
        tracking_number="TRK-SCENARIO8-UPS-8008",
        carrier="UPS",
        status="in_transit",
        shipped_at=NOW - timedelta(days=1),
        estimated_delivery=NOW + timedelta(days=1),
    )
    case8 = Case(
        customer_id=c8.id,
        order_id=o8.id,
        issue_type="cancellation_after_shipment",
        customer_goal="Customer wants to cancel order that has already been dispatched with UPS tracking.",
        status="investigating",
        risk_level="medium",
        current_plan=["check_order_status", "detect_shipment_in_transit", "block_cancellation", "guide_return_flow"],
        current_step="block_cancellation",
        resolution_type="return_on_arrival",
        resolution_status="cancellation_blocked",
        requires_approval=False,
    )
    db.add_all([oi8, sh8, case8])
    db.flush()

    evt8 = AgentEvent(
        case_id=case8.id,
        event_type="CONSTRAINT_DETECTED",
        tool_name="cancel_order",
        input_data={"order_status": "shipped", "tracking": "TRK-SCENARIO8-UPS-8008"},
        output_data={"can_cancel": False, "reason": "Order already in transit with carrier"},
        status="blocked",
        message="Cancellation rejected. Item has shipped; customer advised to initiate return upon delivery.",
    )
    db.add(evt8)

    # -------------------------------------------------------------
    # SCENARIO 9: Verification detects state mismatch
    # -------------------------------------------------------------
    c9 = scenario_customers["scenario9_ian@example.com"]
    p9 = products["ELEC-MECH-KEYBOARD-11"]  # $79.99
    o9 = Order(
        customer_id=c9.id,
        status="refunded",
        total_amount=Decimal("159.98"),  # 2 units = 159.98
        order_date=NOW - timedelta(days=6),
        expected_delivery=NOW - timedelta(days=3),
        actual_delivery=NOW - timedelta(days=3),
        shipping_address="600 SW 5th Ave, Portland, OR 97204",
    )
    db.add(o9)
    db.flush()
    total_order_count += 1

    oi9 = OrderItem(order_id=o9.id, product_id=p9.id, quantity=2, unit_price=p9.price)
    sh9 = Shipment(
        order_id=o9.id,
        tracking_number="TRK-SCENARIO9-FDX-9009",
        carrier="FedEx",
        status="delivered",
        shipped_at=NOW - timedelta(days=5),
        estimated_delivery=NOW - timedelta(days=3),
        actual_delivery=NOW - timedelta(days=3),
    )
    case9 = Case(
        customer_id=c9.id,
        order_id=o9.id,
        issue_type="verification_amount_mismatch",
        customer_goal="Customer requested full refund for both items ($159.98), but simulated refund was for only $79.99.",
        status="verifying",
        risk_level="medium",
        current_plan=["execute_refund", "verify_resolution_state"],
        current_step="verify_resolution_state",
        resolution_type="refund",
        resolution_status="state_mismatch_flagged",
        requires_approval=False,
    )
    db.add_all([oi9, sh9, case9])
    db.flush()

    # Intentionally mismatched refund to trigger verification detection!
    ref9 = Refund(
        order_id=o9.id,
        case_id=case9.id,
        amount=Decimal("79.99"),  # Mismatch! Order total was 159.98
        reason="Partial refund recorded instead of full refund",
        status="completed",
        requires_approval=False,
        approved_by="agent_worker",
    )
    evt9 = AgentEvent(
        case_id=case9.id,
        event_type="VERIFICATION_FAILED",
        tool_name="verify_resolution",
        input_data={"order_total": 159.98, "total_refunded": 79.99},
        output_data={"verified": False, "discrepancy": 79.99},
        status="failure",
        message="Verification detected state mismatch: total refunded ($79.99) does not match requested amount ($159.98).",
    )
    db.add_all([ref9, evt9])

    # -------------------------------------------------------------
    # SCENARIO 10: Simulated action fails and requires replanning
    # -------------------------------------------------------------
    c10 = scenario_customers["scenario10_julia@example.com"]
    p10 = products["HOME-ROBOT-VAC-10"]  # $399.00
    o10 = Order(
        customer_id=c10.id,
        status="delivered",
        total_amount=p10.price,
        order_date=NOW - timedelta(days=8),
        expected_delivery=NOW - timedelta(days=5),
        actual_delivery=NOW - timedelta(days=5),
        shipping_address="701 B St, San Diego, CA 92101",
    )
    db.add(o10)
    db.flush()
    total_order_count += 1

    oi10 = OrderItem(order_id=o10.id, product_id=p10.id, quantity=1, unit_price=p10.price)
    sh10 = Shipment(
        order_id=o10.id,
        tracking_number="TRK-SCENARIO10-DHL-1010",
        carrier="DHL Express",
        status="delivered",
        shipped_at=NOW - timedelta(days=7),
        estimated_delivery=NOW - timedelta(days=5),
        actual_delivery=NOW - timedelta(days=5),
    )
    case10 = Case(
        customer_id=c10.id,
        order_id=o10.id,
        issue_type="action_failure_replanning",
        customer_goal="Replacement vacuum robot dispatch failed via FedEx carrier API (simulated network timeout). Agent must replan to UPS.",
        status="replanning",
        risk_level="medium",
        current_plan=["dispatch_replacement_fedex", "handle_carrier_outage", "replan_carrier_ups", "execute_replacement"],
        current_step="replan_carrier_ups",
        resolution_type="replacement",
        resolution_status="carrier_failover_in_progress",
        requires_approval=False,
    )
    db.add_all([oi10, sh10, case10])
    db.flush()

    evt10_1 = AgentEvent(
        case_id=case10.id,
        event_type="TOOL_CALL",
        tool_name="create_carrier_shipment",
        input_data={"carrier": "FedEx", "service": "Express"},
        output_data={"error": "503 Carrier API Service Unavailable", "retryable": False},
        status="failure",
        message="FedEx API rejected label creation with HTTP 503.",
    )
    evt10_2 = AgentEvent(
        case_id=case10.id,
        event_type="REPLAN_STARTED",
        tool_name="replanner",
        input_data={"failed_tool": "create_carrier_shipment", "failed_carrier": "FedEx"},
        output_data={"selected_backup": "UPS Ground", "estimated_delay": "0 days"},
        status="in_progress",
        message="Agent adapted plan: switching carrier from FedEx to UPS Ground.",
    )
    db.add_all([evt10_1, evt10_2])
    db.flush()

    # -------------------------------------------------------------
    # GENERAL SYNTHETIC ORDERS (Bring total to ~220 orders)
    # -------------------------------------------------------------
    general_customers = all_customers[10:]  # 50 customers
    product_list = list(products.values())
    order_statuses = ["placed", "processing", "shipped", "delivered", "delivered", "delivered", "cancelled", "refunded"]

    # Generate 210 additional orders across general customers
    for i in range(210):
        cust = random.choice(general_customers)
        status = random.choice(order_statuses)
        days_ago = random.randint(1, 45)
        o_date = NOW - timedelta(days=days_ago)

        exp_del = o_date + timedelta(days=random.randint(2, 5))
        act_del = exp_del if status in ("delivered", "refunded") else None

        num_items = random.randint(1, 3)
        selected_prods = random.sample(product_list, num_items)

        items_data = []
        total_amt = Decimal("0.00")
        for p in selected_prods:
            qty = random.randint(1, 2)
            u_price = p.price
            total_amt += u_price * qty
            items_data.append((p, qty, u_price))

        ord_obj = Order(
            customer_id=cust.id,
            status=status,
            total_amount=total_amt,
            order_date=o_date,
            expected_delivery=exp_del,
            actual_delivery=act_del,
            shipping_address=f"{random.randint(100, 9999)} Main St, Apt {random.randint(1, 50)}, Metro City, USA",
        )
        db.add(ord_obj)
        db.flush()
        total_order_count += 1

        for p, qty, u_price in items_data:
            db.add(OrderItem(order_id=ord_obj.id, product_id=p.id, quantity=qty, unit_price=u_price))

        if status in ("shipped", "delivered", "refunded"):
            carrier = random.choice(carriers)
            sh_status = "delivered" if status in ("delivered", "refunded") else "in_transit"
            db.add(
                Shipment(
                    order_id=ord_obj.id,
                    tracking_number=f"TRK-{carrier[:3].upper()}-{random.randint(100000, 999999)}",
                    carrier=carrier,
                    status=sh_status,
                    shipped_at=o_date + timedelta(days=1),
                    estimated_delivery=exp_del,
                    actual_delivery=act_del,
                )
            )

    db.commit()
    return total_order_count


def run_seed():
    print("Beginning NovaCart database seeding...")
    db = SessionLocal()
    try:
        # Clean existing data safely
        print("Clearing any existing domain records...")
        db.query(AgentEvent).delete()
        db.query(Refund).delete()
        db.query(Replacement).delete()
        db.query(Cancellation).delete()
        db.query(Case).delete()
        db.query(Shipment).delete()
        db.query(OrderItem).delete()
        db.query(Order).delete()
        db.query(Inventory).delete()
        db.query(Policy).delete()
        db.query(Product).delete()
        db.query(Warehouse).delete()
        db.query(Customer).delete()
        db.commit()

        print("1. Seeding Warehouses...")
        warehouses = seed_warehouses(db)
        print(f"   Seeded {len(warehouses)} warehouses.")

        print("2. Seeding Products...")
        products = seed_products(db)
        print(f"   Seeded {len(products)} products.")

        print("3. Seeding Inventory matrix...")
        inventories = seed_inventory(db, warehouses, products)
        print(f"   Seeded {len(inventories)} inventory records.")

        print("4. Seeding Customers...")
        scenario_customers, all_customers = seed_customers(db)
        print(f"   Seeded {len(all_customers)} customers ({len(scenario_customers)} scenario customers).")

        print("5. Seeding Policies...")
        policies = seed_policies(db)
        print(f"   Seeded {len(policies)} policies.")

        print("6. Seeding Orders, Shipments, and 10 Agentic Scenarios...")
        order_count = seed_orders_and_scenarios(db, scenario_customers, all_customers, products, warehouses)
        print(f"   Seeded {order_count} total orders with order items and shipments.")

        # Verification counts
        c_count = db.query(Customer).count()
        p_count = db.query(Product).count()
        w_count = db.query(Warehouse).count()
        i_count = db.query(Inventory).count()
        o_count = db.query(Order).count()
        oi_count = db.query(OrderItem).count()
        s_count = db.query(Shipment).count()
        pol_count = db.query(Policy).count()
        case_count = db.query(Case).count()
        ref_count = db.query(Refund).count()
        rep_count = db.query(Replacement).count()
        canc_count = db.query(Cancellation).count()
        evt_count = db.query(AgentEvent).count()

        print("\n=== SEED DATA VERIFICATION SUMMARY ===")
        print(f"Customers:      {c_count}  (Target: 50-100)")
        print(f"Products:       {p_count}")
        print(f"Warehouses:     {w_count}")
        print(f"Inventory:      {i_count}")
        print(f"Orders:         {o_count} (Target: 200-300)")
        print(f"Order Items:    {oi_count}")
        print(f"Shipments:      {s_count}")
        print(f"Policies:       {pol_count}")
        print(f"Cases:          {case_count}")
        print(f"Refunds:        {ref_count}")
        print(f"Replacements:   {rep_count}")
        print(f"Cancellations:  {canc_count}")
        print(f"Agent Events:   {evt_count}")
        print("======================================\n")

    except Exception as exc:
        db.rollback()
        print(f"Error during seeding: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
