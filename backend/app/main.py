from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.exceptions import (
    DomainError,
    ResourceNotFoundError,
    CustomerBlockedError,
    CustomerInactiveError,
    BusinessRuleViolationError,
    InsufficientInventoryError,
    PolicyDenialError,
    OrderStateConflictError,
)
from backend.app.api.routes import (
    health_router,
    customers_router,
    orders_router,
    shipments_router,
    inventory_router,
    policies_router,
    resolutions_router,
    agent_router,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="NovaResolve — Agentic AI Customer Resolution Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers for clean HTTP semantics
@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "ResourceNotFoundError",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(CustomerBlockedError)
async def customer_blocked_handler(request: Request, exc: CustomerBlockedError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "CustomerBlockedError",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(CustomerInactiveError)
async def customer_inactive_handler(request: Request, exc: CustomerInactiveError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "CustomerInactiveError",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(InsufficientInventoryError)
async def insufficient_inventory_handler(request: Request, exc: InsufficientInventoryError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "InsufficientInventoryError",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(OrderStateConflictError)
async def order_state_conflict_handler(request: Request, exc: OrderStateConflictError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "OrderStateConflictError",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(PolicyDenialError)
async def policy_denial_handler(request: Request, exc: PolicyDenialError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "PolicyDenialError",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(BusinessRuleViolationError)
async def business_rule_violation_handler(request: Request, exc: BusinessRuleViolationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "BusinessRuleViolationError",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "DomainError",
            "message": exc.message,
            "details": exc.details,
        },
    )


# Include API Routers under /api
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(customers_router, prefix=settings.API_V1_STR)
app.include_router(orders_router, prefix=settings.API_V1_STR)
app.include_router(shipments_router, prefix=settings.API_V1_STR)
app.include_router(inventory_router, prefix=settings.API_V1_STR)
app.include_router(policies_router, prefix=settings.API_V1_STR)
app.include_router(resolutions_router, prefix=settings.API_V1_STR)
app.include_router(agent_router, prefix=settings.API_V1_STR)


@app.get("/", summary="Root Endpoint")
def root():
    """Returns basic service status."""
    return {
        "service": f"{settings.PROJECT_NAME} API",
        "status": "running",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
