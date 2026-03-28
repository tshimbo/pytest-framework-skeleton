"""Validates trading orders before submission.

WHY THIS FILE EXISTS:
    Before an order reaches the exchange, it must be validated.
    You wouldn't let someone buy -50 shares or submit an order for "BANANA" stock.
    This validator catches bad data EARLY — before it causes problems downstream.

    In a real trading system at Citadel Securities, validation happens at multiple
    layers: the client, the OMS (Order Management System), and the exchange itself.
    This file represents the OMS-level validation.

KEY PYTHON CONCEPTS DEMONSTRATED:
    1. Custom Exception classes  — ValidationError stores WHICH field failed
    2. Private functions (_prefix) — convention for internal-only helpers
    3. Guard clauses             — return/raise early to keep code flat
    4. Set membership (`in`)     — O(1) lookup for valid symbols
    5. Type hints                — every function signature is fully typed

TESTING PATTERN:
    The validator is designed to be easy to test with @pytest.mark.parametrize.
    Each validation rule maps to a test case:
        - Empty symbol     → ValidationError(field="symbol")
        - Zero quantity    → ValidationError(field="quantity")
        - Negative price   → ValidationError(field="price")
    The 'field' attribute lets tests assert WHICH validation failed, not just THAT it failed.
"""

# ─── IMPORTS ────────────────────────────────────────────────────────────────
from typing import Optional    # Optional[str] = str or None
from src.models.order import Order, OrderType  # Our Order dataclass and its types

# ─── CONSTANTS ──────────────────────────────────────────────────────────────
# Maximum allowed quantity for a single order.
# In real trading, exchanges enforce "fat finger" checks to prevent
# accidental orders like "buy 999,999,999 shares of AAPL".
# The underscore in 1_000_000 is Python syntax sugar — it's just 1000000
# but way more readable. Python ignores the underscores.
MAX_QUANTITY = 1_000_000

# Valid symbols — a Python SET (not list).
# Sets use hash tables internally, so `"AAPL" in VALID_SYMBOLS` is O(1) constant time.
# A list would be O(n) — checking every element. For 16 symbols it doesn't matter,
# but for 10,000 symbols on a real exchange, the difference is huge.
#
# In production, this would come from a reference data service (e.g., Bloomberg)
# that updates daily when new stocks get listed or old ones get delisted.
VALID_SYMBOLS = {
    "AAPL", "GOOGL", "MSFT", "AMZN", "META", "TSLA", "NVDA",  # Big tech
    "JPM", "BAC", "WFC", "GS", "MS",                            # Banks
    "SPY", "QQQ", "IWM", "DIA",                                  # ETFs
}


# ─── CUSTOM EXCEPTION ───────────────────────────────────────────────────────
# We create our OWN exception class instead of using the built-in ValueError.
# Why? Because our exception carries extra information:
#   - exc.field   = which field was invalid ("symbol", "quantity", "price")
#   - exc.message = a human-readable description
#
# This makes tests much more precise:
#   with pytest.raises(ValidationError) as exc_info:
#       validate_order(bad_order)
#   assert exc_info.value.field == "quantity"   ← we know EXACTLY what failed
#
# If we used plain ValueError, we'd only have the message string to check,
# which is brittle (changes if you reword the message).
class ValidationError(Exception):
    """Raised when order validation fails.

    Attributes:
        field:   The name of the invalid field (e.g., "symbol", "quantity", "price")
        message: Human-readable explanation of what went wrong
    """

    def __init__(self, field: str, message: str) -> None:
        self.field = field       # Store which field is bad
        self.message = message   # Store why it's bad
        # super().__init__() calls Exception's __init__ with a formatted string.
        # This means str(exc) and repr(exc) will show something useful:
        #   "Validation error on 'quantity': Quantity must be positive, got -5."
        super().__init__(f"Validation error on '{field}': {message}")


# ─── PUBLIC API ─────────────────────────────────────────────────────────────
# This is the ONLY function external code should call.
# It orchestrates the private validators below in a specific order.
def validate_order(order: Order) -> bool:
    """Validate an order and raise ValidationError if invalid.

    Validation order matters:
        1. Symbol first — if the stock doesn't exist, nothing else matters
        2. Quantity second — even valid stocks need a valid quantity
        3. Price last — depends on order_type context

    Args:
        order: The Order object to validate.

    Returns:
        True if the order passes all validation checks.

    Raises:
        ValidationError: If any field is invalid. Check exc.field and exc.message.
    """
    _validate_symbol(order.symbol)           # Step 1: Is the symbol valid?
    _validate_quantity(order.quantity)        # Step 2: Is the quantity valid?
    _validate_price(order.price, order.order_type)  # Step 3: Is the price valid for this order type?
    return True  # If we get here without raising, the order is valid


# ─── PRIVATE VALIDATORS ─────────────────────────────────────────────────────
# The underscore prefix (_validate_symbol) is a Python convention meaning
# "this function is internal — don't call it from outside this module."
# It's not enforced by the language, but tools like linters will warn you.

def _validate_symbol(symbol: Optional[str]) -> None:
    """Symbol must be a non-empty string in the valid set.

    Guard clause pattern:
        Check the bad cases first and raise immediately.
        If execution reaches the end of the function, the input is valid.
        This keeps the code flat (no deeply nested if/else).
    """
    # Guard 1: Symbol is None, empty string "", or whitespace "   "
    # The `not symbol` check handles both None and empty string:
    #   not None  → True
    #   not ""    → True
    #   not "AAPL" → False
    if not symbol or not symbol.strip():
        raise ValidationError("symbol", "Symbol is required and cannot be empty.")

    # Guard 2: Symbol is not in our valid set (O(1) lookup)
    if symbol not in VALID_SYMBOLS:
        raise ValidationError(
            "symbol",
            f"Unknown symbol '{symbol}'. Must be one of: {sorted(VALID_SYMBOLS)}"
        )
    # If we get here, symbol is valid — function returns None implicitly


def _validate_quantity(quantity: int) -> None:
    """Quantity must be a positive integer within MAX_QUANTITY.

    Real-world context:
        Exchanges reject orders with qty ≤ 0 (makes no sense to buy 0 shares).
        They also reject "fat finger" orders (accidentally typing 1,000,000 instead of 1,000).
    """
    if quantity <= 0:
        raise ValidationError("quantity", f"Quantity must be positive, got {quantity}.")
    if quantity > MAX_QUANTITY:
        raise ValidationError("quantity", f"Quantity {quantity} exceeds maximum of {MAX_QUANTITY}.")


def _validate_price(price: Optional[float], order_type: OrderType) -> None:
    """Price validation depends on order type.

    Rules:
        LIMIT / GTC orders → price is REQUIRED and must be > 0
        MARKET orders      → price is OPTIONAL (exchange decides the price)
        All orders         → price can never be negative

    This is a real business rule from the FIX protocol:
        Tag 44 (Price) is required when OrdType (tag 40) = 2 (Limit)
        Tag 44 is NOT required when OrdType = 1 (Market)
    """
    # Check 1: LIMIT and GTC orders MUST have a price
    if order_type in (OrderType.LIMIT, OrderType.GTC):
        if price is None:
            raise ValidationError("price", f"Price is required for {order_type.value} orders.")
        if price <= 0:
            raise ValidationError("price", f"Price must be positive, got {price}.")

    # Check 2: Even for MARKET orders, if a price IS provided, it can't be negative
    if price is not None and price < 0:
        raise ValidationError("price", f"Price cannot be negative, got {price}.")
