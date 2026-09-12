"""Live Gemini API Smoke Test Script for NovaResolve Phase 5.

Usage:
1. Ensure your local .env file contains:
   GEMINI_API_KEY=your_actual_gemini_api_key
   LLM_PROVIDER=gemini
   LLM_MODEL=gemini-1.5-flash
2. Run from project root:
   python scripts/smoke_test_gemini.py
"""

import sys
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.db.models.customer import Customer
from backend.app.db.models.order import Order, OrderItem
from backend.app.db.models.shipment import Shipment
from backend.app.db.models.product import Product
from backend.app.db.models.warehouse import Warehouse
from backend.app.db.models.inventory import Inventory
from backend.app.db.models.case import Case
from agents.runtime.agent import NovaResolveAgent
from agents.planning.decision_provider import DecisionProviderFactory


def run_smoke_test():
    print("=" * 70)
    print(" NovaResolve — Live Google Gemini LLM Smoke Test (Phase 5)")
    print("=" * 70)

    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
        print("\n[!] GEMINI_API_KEY is not configured in your environment or .env file.")
        print("    To run this live test:")
        print("    1. Get a free API key at: https://aistudio.google.com/")
        print("    2. Add to your local .env file:")
        print("       GEMINI_API_KEY=your_api_key_here")
        print("       LLM_PROVIDER=gemini")
        print("       LLM_MODEL=gemini-1.5-flash")
        print("    3. Run: python scripts/smoke_test_gemini.py\n")
        return

    print(f"[*] Provider: {settings.LLM_PROVIDER}")
    print(f"[*] Model:    {settings.LLM_MODEL}")
    print(f"[*] Timeout:  {settings.LLM_TIMEOUT_SECONDS}s")
    print("\n[1] Setting up simulated customer scenario in database...")

    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:6]
        customer = Customer(
            name=f"Smoke Test User {uid}",
            email=f"smoke_{uid}@example.com",
            status="active",
        )
        db.add(customer)
        db.flush()

        order = Order(
            customer_id=customer.id,
            total_amount=Decimal("49.99"),
            status="delivered",
            shipping_address="123 Live Gemini Way, Mountain View, CA",
            order_date=datetime.now(timezone.utc) - timedelta(days=3),
        )
        db.add(order)
        db.flush()

        product = db.query(Product).first()
        if not product:
            print("[!] No products found in DB. Run seed first: python -m db.seed.seed_data")
            return

        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=1,
            unit_price=Decimal("49.99"),
        )
        db.add(order_item)
        db.flush()

        shipment = Shipment(
            order_id=order.id,
            tracking_number=f"TRK-LIVE-{uid}",
            status="delivered",
            carrier="UPS",
        )
        db.add(shipment)
        db.flush()

        case = Case(
            customer_id=customer.id,
            order_id=order.id,
            issue_type="refund",
            customer_goal="My package was damaged upon arrival. Please issue a refund.",
            status="open",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        print(f"[+] Created Case ID: {case.id}")
        print(f"[+] Customer Goal:   \"{case.customer_goal}\"")
        print(f"[+] Order Total:     ${order.total_amount}")

        print("\n[2] Executing NovaResolveAgent with live LLM decision provider...")
        provider = DecisionProviderFactory.get_default_provider()
        print(f"[+] Decision Provider initialized: {provider.name} ({provider.provider_type})")

        result = NovaResolveAgent.run(db=db, case_id=case.id, decision_provider=provider)

        print("\n" + "=" * 70)
        print(" Agent Execution Outcome")
        print("=" * 70)
        print(f" Success:            {result.success}")
        print(f" Status:             {result.status}")
        print(f" Resolution Status:  {result.resolution_status}")
        print(f" Requires Approval:  {result.requires_approval}")
        print(f" Steps Executed:     {result.steps_executed}")
        print(f" Final Outcome:      {result.final_outcome}")

        if result.execution_trace:
            print("\n Execution Trace:")
            for step in result.execution_trace:
                source = step.get("source", "unknown")
                print(f"   Step {step['step']}: [{step['tool_name']}] (source={source})")
                print(f"     Rationale:   {step.get('rationale')}")
                print(f"     Observation: {step.get('observation_status')} - {step.get('observation_message')}")

        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    run_smoke_test()
