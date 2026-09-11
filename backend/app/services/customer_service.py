import uuid
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.db.models.customer import Customer
from backend.app.core.exceptions import (
    ResourceNotFoundError,
    CustomerBlockedError,
    CustomerInactiveError,
)


class CustomerService:
    @staticmethod
    def get_customer_by_id(db: Session, customer_id: uuid.UUID) -> Customer:
        """Retrieves a customer by UUID or raises ResourceNotFoundError."""
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise ResourceNotFoundError(f"Customer with ID '{customer_id}' was not found.")
        return customer

    @staticmethod
    def get_customer_by_email(db: Session, email: str) -> Customer:
        """Retrieves a customer by email address or raises ResourceNotFoundError."""
        customer = db.query(Customer).filter(Customer.email == email.strip().lower()).first()
        if not customer:
            raise ResourceNotFoundError(f"Customer with email '{email}' was not found.")
        return customer

    @staticmethod
    def validate_active_requester(customer: Customer) -> None:
        """Validates that customer is not blocked and has an active status."""
        if customer.status == "blocked":
            raise CustomerBlockedError(
                f"Customer '{customer.id}' is blocked and cannot initiate resolution requests.",
                details={"customer_id": str(customer.id), "status": customer.status},
            )
        if customer.status != "active":
            raise CustomerInactiveError(
                f"Customer '{customer.id}' is inactive.",
                details={"customer_id": str(customer.id), "status": customer.status},
            )
