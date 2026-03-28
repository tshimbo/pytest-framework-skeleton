"""Order model representing a trading order."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import uuid
from datetime import datetime


class Side(Enum):
    """Order side: BUY or SELL."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type classification."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    IOC = "IOC"       # Immediate or Cancel
    FOK = "FOK"       # Fill or Kill
    GTC = "GTC"       # Good Till Cancel


class OrderStatus(Enum):
    """Current status of an order."""
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    """Represents a trading order.

    Attributes:
        symbol: The ticker symbol (e.g., 'AAPL').
        side: BUY or SELL.
        quantity: Number of shares/units. Must be > 0.
        price: Limit price. Required for LIMIT/GTC orders. Must be > 0 if set.
        order_type: The type of order.
        order_id: Unique identifier, auto-generated if not provided.
        status: Current order status.
        filled_quantity: Number of shares filled so far.
        created_at: Timestamp when order was created.
    """
    symbol: str
    side: Side
    quantity: int
    price: Optional[float] = None
    order_type: OrderType = OrderType.LIMIT
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderStatus = OrderStatus.NEW
    filled_quantity: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def remaining_quantity(self) -> int:
        """Shares remaining to be filled."""
        return self.quantity - self.filled_quantity

    @property
    def is_complete(self) -> bool:
        """Whether the order is in a terminal state."""
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        )
