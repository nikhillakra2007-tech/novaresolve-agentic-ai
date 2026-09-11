from uuid import UUID
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.customer import CustomerResponse
from backend.app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get Customer by ID",
    description="Fetches a customer profile by primary key UUID. Validates existence and active status.",
)
def get_customer_by_id(
    customer_id: UUID = Path(..., description="Unique customer UUID"),
    db: Session = Depends(get_db),
):
    customer = CustomerService.get_customer_by_id(db, customer_id)
    return customer


@router.get(
    "/by-email/{email}",
    response_model=CustomerResponse,
    summary="Get Customer by Email",
    description="Looks up a customer profile by case-insensitive email address.",
)
def get_customer_by_email(
    email: str = Path(..., description="Customer email address"),
    db: Session = Depends(get_db),
):
    customer = CustomerService.get_customer_by_email(db, email)
    return customer
