"""Unit-level conftest.py — fixtures specific to unit tests.

This demonstrates conftest hierarchy:
  tests/conftest.py          → available to ALL tests
  tests/unit/conftest.py     → available to tests/unit/** only
  tests/integration/conftest.py → available to tests/integration/** only
"""

import pytest

from src.models.order import Order, Side, OrderType


@pytest.fixture
def cancelled_order() -> Order:
    """An order that has already been cancelled — unit test specific."""
    from src.models.order import OrderStatus
    order = Order(
        symbol="TSLA",
        side=Side.SELL,
        quantity=75,
        price=200.00,
        order_type=OrderType.LIMIT,
    )
    order.status = OrderStatus.CANCELLED
    return order


@pytest.fixture
def bulk_orders(make_order):
    """Generate a list of 10 diverse orders for batch-testing.

    Uses the `make_order` factory from the root conftest.
    """
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "META",
               "TSLA", "NVDA", "JPM", "BAC", "SPY"]
    orders = []
    for i, sym in enumerate(symbols):
        orders.append(make_order(
            symbol=sym,
            quantity=(i + 1) * 100,
            price=100.0 + i * 10,
            side=Side.BUY if i % 2 == 0 else Side.SELL,
        ))
    return orders
