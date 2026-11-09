class NetArchitectException(Exception):
    """Base exception for NetArchitect operations."""
    pass


class PhysicalDistanceViolationError(NetArchitectException):
    """Raised when physical transmission media boundaries are violated (e.g., Cat6a >100m)."""
    pass


class SubnetExhaustionError(NetArchitectException):
    """Raised when total requested host allocations exceed the root CIDR block capacity."""
    pass