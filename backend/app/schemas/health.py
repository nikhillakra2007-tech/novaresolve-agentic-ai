from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    status: str = Field(..., description="Status of the database connection: connected, disconnected")
    latency_ms: Optional[float] = Field(None, description="Roundtrip query latency in milliseconds")
    pool: Optional[Dict[str, Any]] = Field(None, description="Engine connection pool statistics")
    error: Optional[str] = Field(None, description="Error message if disconnected")


class HealthResponse(BaseModel):
    service: str = Field("NovaCart API", description="Name of the service")
    status: str = Field(..., description="Overall health: healthy, degraded, unhealthy")
    environment: str = Field(..., description="Application environment")
    version: str = Field("1.0.0", description="API version")
    database: DatabaseHealth = Field(..., description="Database connectivity details")
