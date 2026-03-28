"""Unit-level conftest.py — fixtures specific to unit tests.

WHAT MAKES THIS DIFFERENT FROM THE ROOT conftest.py?
    Fixtures defined HERE are only available to tests inside tests/unit/.
    Tests in tests/integration/ CANNOT see these fixtures.

    This is the conftest HIERARCHY in action:
        tests/conftest.py              → ALL tests can use these fixtures
        tests/unit/conftest.py         → ONLY tests/unit/** can use these  ← THIS FILE
        tests/integration/conftest.py  → ONLY tests/integration/** can use these

    When a unit test requests a fixture, pytest searches:
        1. The test file itself
        2. tests/unit/conftest.py  (this file)
        3. tests/conftest.py       (parent conftest)
        4. Installed plugins

IMPORTANT CONCEPT: FIXTURE COMPOSITION
    The `bulk_orders` fixture below depends on `make_order` (from root conftest).
    pytest resolves this automatically — it sees that `bulk_orders` needs `make_order`,
    looks up `make_order` in the fixture registry, creates it, and injects it.
    This is called FIXTURE COMPOSITION or FIXTURE CHAINING.
"""

import pytest

from src.models.order import Order, Side, OrderType


@pytest.fixture
def cancelled_order() -> Order:
    """An order that has already been cancelled — unit test specific.

    WHY IS THIS IN THE UNIT CONFTEST?
        Only unit tests need a pre-cancelled order. Integration tests
        don't test cancellation yet. By putting it here, we keep
        the root conftest clean and avoid cluttering the global fixture namespace.

    NOTE ON MANUAL STATUS SETTING:
        We create a normal order then manually set its status to CANCELLED.
        In a real system, cancellation would happen through an API call.
        In unit tests, we skip the API and set state directly — that's the point
        of unit testing: test the logic in isolation.
    """
    from src.models.order import OrderStatus
    order = Order(
        symbol="TSLA",
        side=Side.SELL,
        quantity=75,
        price=200.00,
        order_type=OrderType.LIMIT,
    )
    # Manually transition to CANCELLED state (skipping the normal lifecycle)
    order.status = OrderStatus.CANCELLED
    return order


@pytest.fixture
def bulk_orders(make_order):
    """Generate a list of 10 diverse orders for batch-testing.

    FIXTURE COMPOSITION IN ACTION:
        This fixture's parameter `make_order` is itself a fixture
        (defined in tests/conftest.py). pytest automatically:
            1. Sees that `bulk_orders` needs `make_order`
            2. Creates `make_order` first
            3. Passes it to this function

        This is like dependency injection in Spring or Angular —
        you declare what you need, and the framework provides it.

    WHAT THIS CREATES:
        10 orders with different symbols, quantities, prices, and sides.
        Used by test_bulk_validation to prove the validator handles
        a diverse set of valid orders without errors.

        Order 0: AAPL, BUY,  qty=100,  price=100
        Order 1: GOOGL, SELL, qty=200,  price=110
        Order 2: MSFT, BUY,  qty=300,  price=120
        ... and so on
    """
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "META",
               "TSLA", "NVDA", "JPM", "BAC", "SPY"]
    orders = []
    for i, sym in enumerate(symbols):
        orders.append(make_order(
            symbol=sym,
            quantity=(i + 1) * 100,        # 100, 200, 300, ..., 1000
            price=100.0 + i * 10,           # 100, 110, 120, ..., 190
            side=Side.BUY if i % 2 == 0 else Side.SELL,  # Alternating BUY/SELL
        ))
    return orders
