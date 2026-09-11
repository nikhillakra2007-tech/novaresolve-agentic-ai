from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.customers import router as customers_router
from backend.app.api.routes.orders import router as orders_router
from backend.app.api.routes.shipments import router as shipments_router
from backend.app.api.routes.inventory import router as inventory_router
from backend.app.api.routes.policies import router as policies_router
from backend.app.api.routes.resolutions import router as resolutions_router
from backend.app.api.routes.agent import router as agent_router

__all__ = [
    "health_router",
    "customers_router",
    "orders_router",
    "shipments_router",
    "inventory_router",
    "policies_router",
    "resolutions_router",
    "agent_router",
]
