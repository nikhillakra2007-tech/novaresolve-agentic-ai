"""Domain exceptions for NovaResolve.

These exceptions map domain and business rule violations to clear HTTP semantics.
"""

from typing import Optional, Any, Dict


class DomainError(Exception):
    """Base domain exception."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ResourceNotFoundError(DomainError):
    """Raised when a requested resource (customer, order, shipment, etc.) does not exist."""
    pass


class CustomerBlockedError(DomainError):
    """Raised when an action is attempted for a blocked customer."""
    pass


class CustomerInactiveError(DomainError):
    """Raised when an action is attempted for an inactive customer."""
    pass


class BusinessRuleViolationError(DomainError):
    """Raised when an operation violates business constraints."""
    pass


class InsufficientInventoryError(DomainError):
    """Raised when a requested warehouse cannot satisfy replacement quantity."""
    pass


class PolicyDenialError(DomainError):
    """Raised when an operation is disallowed by business policy."""
    pass


class OrderStateConflictError(DomainError):
    """Raised when an order state forbids the action (e.g. cancelling shipped order)."""
    pass
