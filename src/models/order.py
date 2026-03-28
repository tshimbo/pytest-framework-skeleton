"""Order model representing a trading order.

WHY THIS FILE EXISTS:
    In any trading system, an "order" is the fundamental unit of work.
    This file defines the Order class — a blueprint for every buy/sell request
    that flows through the system. Think of it like a form you fill out:
    "I want to BUY 100 shares of AAPL at $150.50."

    We use Python's @dataclass decorator to avoid writing boilerplate __init__,
    __repr__, and __eq__ methods. The Enum classes enforce that fields like
    'side' can ONLY be BUY or SELL — you can't accidentally set it to "BANANA".

KEY PYTHON CONCEPTS DEMONSTRATED:
    1. @dataclass       — auto-generates __init__, __repr__, __eq__
    2. Enum             — restricts a field to a fixed set of values
    3. Optional[T]      — type hint meaning "this can be T or None"
    4. field()          — customize how a dataclass field is initialised
    5. default_factory  — a function called to generate a default value
    6. @property        — makes a method look like an attribute (order.remaining_quantity)
    7. uuid4()          — generates a random unique ID (e.g., "a3f2b1c4-...")

HOW THIS MAPS TO CITADEL SECURITIES:
    Real trading systems have Order objects flowing through OMS (Order Management
    Systems). Interviewers will ask you to model an order, track its lifecycle
    (NEW → PARTIALLY_FILLED → FILLED), and write tests for edge cases.
"""

# ─── IMPORTS ────────────────────────────────────────────────────────────────
# dataclass: decorator that auto-generates __init__(), __repr__(), __eq__()
# field:     lets us customise individual fields (e.g., auto-generate an ID)
from dataclasses import dataclass, field

# Enum: a class where each member is a named constant.
# Prevents typos — Side.BUY is valid, Side.BANANA would raise an AttributeError.
from enum import Enum

# Optional[float] means the type is either float OR None.
# We use it for 'price' because MARKET orders don't need a price.
from typing import Optional

# uuid4() generates a random UUID like "a3f2b1c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c"
# Every order gets a unique ID so we can track it through the system.
import uuid

# datetime.utcnow() gives the current time in UTC — important for trading
# because exchanges in different time zones need a common reference.
from datetime import datetime


# ─── ENUM: Side ─────────────────────────────────────────────────────────────
# In trading, every order is either a BUY or a SELL. That's it. No other option.
# Using an Enum guarantees this at the type level.
#
# Usage:  order.side = Side.BUY     ✅
#         order.side = "BUY"        ❌ (type checker would warn)
#         order.side = Side.BANANA  ❌ (AttributeError at runtime)
class Side(Enum):
    """Order side: BUY or SELL."""
    BUY = "BUY"    # Buyer wants to purchase shares
    SELL = "SELL"  # Seller wants to sell shares they own


# ─── ENUM: OrderType ────────────────────────────────────────────────────────
# Different order types tell the exchange HOW to execute the order.
# This is directly from the FIX protocol (which you'll use in Project 5).
class OrderType(Enum):
    """Order type classification.

    These map to FIX protocol OrdType (tag 40) values:
        MARKET = '1'  — execute immediately at best available price
        LIMIT  = '2'  — execute only at specified price or better
        IOC    = 'immediate or cancel' — fill what you can, cancel the rest
        FOK    = 'fill or kill' — fill the ENTIRE order or cancel it all
        GTC    = 'good till cancel' — keep the order open until explicitly cancelled
    """
    MARKET = "MARKET"  # No price needed — "just buy it at whatever price"
    LIMIT = "LIMIT"    # Price required — "buy only if price ≤ $150.50"
    IOC = "IOC"        # Immediate or Cancel — partial fills OK, cancel remainder
    FOK = "FOK"        # Fill or Kill — all or nothing, no partial fills
    GTC = "GTC"        # Good Till Cancel — stays open indefinitely


# ─── ENUM: OrderStatus ──────────────────────────────────────────────────────
# An order moves through a lifecycle. This enum tracks where it is.
# The flow is typically:  NEW → PARTIALLY_FILLED → FILLED
#                     or: NEW → CANCELLED
#                     or: NEW → REJECTED (if validation fails at exchange)
class OrderStatus(Enum):
    """Current status of an order in its lifecycle."""
    NEW = "NEW"                          # Just created, not yet sent to exchange
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Some shares filled, some remaining
    FILLED = "FILLED"                    # All shares filled — TERMINAL STATE
    CANCELLED = "CANCELLED"              # User cancelled it — TERMINAL STATE
    REJECTED = "REJECTED"                # Exchange rejected it — TERMINAL STATE


# ─── DATACLASS: Order ───────────────────────────────────────────────────────
# @dataclass automatically generates:
#   __init__()  — so we can do Order(symbol="AAPL", side=Side.BUY, quantity=100)
#   __repr__()  — so print(order) shows all fields nicely
#   __eq__()    — so two orders with the same fields are considered equal
#
# Fields WITHOUT defaults must come BEFORE fields WITH defaults.
# That's why symbol, side, quantity are first (required) and
# price, order_type, etc. are after (have defaults).
@dataclass
class Order:
    """Represents a trading order.

    Attributes:
        symbol:          The ticker symbol (e.g., 'AAPL', 'GOOGL').
        side:            BUY or SELL.
        quantity:        Number of shares/units. Must be > 0.
        price:           Limit price. Required for LIMIT/GTC orders. None for MARKET.
        order_type:      How the exchange should execute this order.
        order_id:        Unique identifier, auto-generated via uuid4 if not provided.
        status:          Current lifecycle state (NEW, FILLED, etc.).
        filled_quantity:  Number of shares that have been filled so far.
        created_at:      UTC timestamp when this order object was created.

    Example:
        >>> order = Order(symbol="AAPL", side=Side.BUY, quantity=100, price=150.50)
        >>> order.remaining_quantity
        100
        >>> order.is_complete
        False
    """

    # ── Required fields (no default — caller MUST provide these) ────────
    symbol: str        # e.g., "AAPL", "GOOGL", "MSFT"
    side: Side         # Side.BUY or Side.SELL
    quantity: int      # Number of shares — e.g., 100

    # ── Optional fields (have defaults — caller CAN override) ───────────
    price: Optional[float] = None
    # Optional[float] means this is either a float or None.
    # MARKET orders don't need a price, so we default to None.

    order_type: OrderType = OrderType.LIMIT
    # Default to LIMIT because it's the most common order type.

    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # field(default_factory=...) means "call this function to generate the default".
    # We use a lambda so each Order gets its OWN unique ID.
    # Without default_factory, all orders would share the SAME ID!
    #
    # WHY NOT just `order_id: str = str(uuid.uuid4())`?
    # Because that would evaluate ONCE at class definition time,
    # and every instance would get the same UUID. default_factory
    # ensures the lambda runs fresh for each new Order.

    status: OrderStatus = OrderStatus.NEW
    # Every order starts as NEW. It moves to other states as it's processed.

    filled_quantity: int = 0
    # Starts at 0. Incremented as the exchange fills portions of the order.

    created_at: datetime = field(default_factory=datetime.utcnow)
    # Records when this Order object was created. Uses UTC to avoid timezone issues.
    # In a real system, this would be the timestamp the OMS received the order.

    # ── Computed Properties ─────────────────────────────────────────────
    # @property makes a method accessible like an attribute:
    #   order.remaining_quantity   (NOT order.remaining_quantity())
    # This is useful when the value is derived from other fields.

    @property
    def remaining_quantity(self) -> int:
        """How many shares are left to be filled.

        Example:
            order.quantity = 100, order.filled_quantity = 30
            → remaining_quantity = 70
        """
        return self.quantity - self.filled_quantity

    @property
    def is_complete(self) -> bool:
        """Whether the order is in a terminal state (no further action possible).

        Terminal states: FILLED, CANCELLED, REJECTED.
        Non-terminal states: NEW, PARTIALLY_FILLED (still has remaining quantity).

        This is used in tests to verify order lifecycle transitions:
            assert not new_order.is_complete
            new_order.status = OrderStatus.FILLED
            assert new_order.is_complete
        """
        return self.status in (
            OrderStatus.FILLED,      # Fully executed
            OrderStatus.CANCELLED,   # User cancelled
            OrderStatus.REJECTED,    # Exchange rejected
        )
