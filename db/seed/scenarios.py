"""Definitions and metadata for the 10 deliberate agentic test scenarios.

Each scenario is pre-seeded with specific customers, orders, inventory states,
and case states so agentic workflows, evaluators, and verifiers can run deterministically.
"""

from typing import Dict, Any

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "scenario_1_replacement_success": {
        "title": "Replacement succeeds normally",
        "description": "Defective item; primary warehouse has ample stock (quantity > 10). Low risk.",
        "customer_email": "scenario1_alice@example.com",
        "product_sku": "AUD-NC-HEADPHONES-01",
        "warehouse_name": "Dallas Central Warehouse",
        "expected_risk": "low",
        "requires_approval": False,
    },
    "scenario_2_replacement_alternate_warehouse": {
        "title": "Replacement fails at primary warehouse but succeeds via alternate warehouse",
        "description": "Primary warehouse (Dallas) has 0 quantity, but Reno West has 15 units. Agent must detect constraint and replan.",
        "customer_email": "scenario2_bob@example.com",
        "product_sku": "ELEC-4K-MONITOR-02",
        "primary_warehouse": "Dallas Central Warehouse",
        "alternate_warehouse": "Reno West Warehouse",
        "expected_risk": "medium",
        "requires_approval": False,
    },
    "scenario_3_refund_below_threshold": {
        "title": "Refund below approval threshold (< $100)",
        "description": "Damaged USB-C hub priced at $45.00. Automatic refund permitted under return policy.",
        "customer_email": "scenario3_charlie@example.com",
        "product_sku": "ACC-USB-C-DOCK-03",
        "order_amount": 45.00,
        "policy_threshold": 100.00,
        "expected_risk": "low",
        "requires_approval": False,
    },
    "scenario_4_refund_exceeds_threshold": {
        "title": "Refund exceeds approval threshold (>= $100)",
        "description": "Faulty flagship smart projector priced at $520.00. Requires human approval before refund execution.",
        "customer_email": "scenario4_diana@example.com",
        "product_sku": "ELEC-SMART-PROJ-04",
        "order_amount": 520.00,
        "policy_threshold": 100.00,
        "expected_risk": "high",
        "requires_approval": True,
    },
    "scenario_5_order_delayed": {
        "title": "Order delayed in transit",
        "description": "Shipment has status 'delayed' with estimated delivery date past today. Triggers carrier tracer or expedited re-ship.",
        "customer_email": "scenario5_evan@example.com",
        "shipment_status": "delayed",
        "expected_risk": "medium",
    },
    "scenario_6_delivered_damaged": {
        "title": "Order delivered but customer reports damage",
        "description": "Shipment status is 'delivered'. Customer goal is replacement or refund due to cracked screen.",
        "customer_email": "scenario6_fiona@example.com",
        "product_sku": "ELEC-TABLET-10INCH-05",
        "expected_risk": "low",
    },
    "scenario_7_cancellation_allowed": {
        "title": "Order cancellation allowed",
        "description": "Order was just placed (status 'placed'), warehouse hasn't fulfilled, no tracking label created. Cancellation succeeds.",
        "customer_email": "scenario7_george@example.com",
        "order_status": "placed",
        "can_cancel": True,
        "expected_risk": "low",
    },
    "scenario_8_cancellation_blocked": {
        "title": "Order cancellation blocked because order shipped",
        "description": "Order is already 'shipped' with carrier tracking in transit. Agent must refuse cancellation and guide return workflow.",
        "customer_email": "scenario8_hannah@example.com",
        "order_status": "shipped",
        "shipment_status": "in_transit",
        "can_cancel": False,
        "expected_risk": "medium",
    },
    "scenario_9_verification_mismatch": {
        "title": "Verification detects a state mismatch",
        "description": "Simulated resolution marked order refunded for $60.00, but order total was $180.00. Verifier must flag verification failure.",
        "customer_email": "scenario9_ian@example.com",
        "expected_discrepancy": "amount_mismatch",
    },
    "scenario_10_action_failure_replanning": {
        "title": "Simulated action fails and requires replanning",
        "description": "Simulated shipment API throws 503 carrier outage. Agent records CONSTRAINT_DETECTED, enters REPLANNING, and selects alternative carrier.",
        "customer_email": "scenario10_julia@example.com",
        "initial_carrier": "FedEx",
        "backup_carrier": "UPS",
    },
}
