"""Validates trading orders before submission."""

from typing import Optional
from src.models.order import Order, OrderType

# Maximum allowed quantity for a single order
MAX_QUANTITY = 1_000_000

# Valid symbols (in a real system this would come from a reference data service)
VALID_SYMBOLS = {
    "AAPL", "GOOGL", "MSFT", "AMZN", "META", "TSLA", "NVDA",
    "JPM", "BAC", "WFC", "GS", "MS",
    "SPY", "QQQ", "IWM", "DIA",
}


class ValidationError(Exception):
    """Raised when order validation fails."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"Validation error on '{field}': {message}")


def validate_order(order: Order) -> bool:
    """Validate an order and raise ValidationError if invalid.

    Args:
        order: The order to validate.

    Returns:
        True if the order is valid.

    Raises:
        ValidationError: If any field is invalid.
    """
    _validate_symbol(order.symbol)
    _validate_quantity(order.quantity)
    _validate_price(order.price, order.order_type)
    return True


def _validate_symbol(symbol: Optional[str]) -> None:
    """Symbol must be a non-empty string in the valid set."""
    if not symbol or not symbol.strip():
        raise ValidationError("symbol", "Symbol is required and cannot be empty.")
    if symbol not in VALID_SYMBOLS:
        raise ValidationError("symbol", f"Unknown symbol '{symbol}'. Must be one of: {sorted(VALID_SYMBOLS)}")


def _validate_quantity(quantity: int) -> None:
    """Quantity must be a positive integer within MAX_QUANTITY."""
    if quantity <= 0:
        raise ValidationError("quantity", f"Quantity must be positive, got {quantity}.")
    if quantity > MAX_QUANTITY:
        raise ValidationError("quantity", f"Quantity {quantity} exceeds maximum of {MAX_QUANTITY}.")


def _validate_price(price: Optional[float], order_type: OrderType) -> None:
    """Price must be positive for LIMIT/GTC orders. Optional for MARKET."""
    if order_type in (OrderType.LIMIT, OrderType.GTC):
        if price is None:
            raise ValidationError("price", f"Price is required for {order_type.value} orders.")
        if price <= 0:
            raise ValidationError("price", f"Price must be positive, got {price}.")
    if price is not None and price < 0:
        raise ValidationError("price", f"Price cannot be negative, got {price}.")
