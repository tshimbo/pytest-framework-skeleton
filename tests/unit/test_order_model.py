"""Tests for the Order model using shared fixtures from conftest hierarchy.

WHAT THIS FILE TESTS:
    The Order dataclass from src/models/order.py:
    - Can we create orders with the right fields?
    - Do computed properties (remaining_quantity, is_complete) work?
    - Does the factory fixture produce unique orders?
    - Does the session-scoped fixture persist across tests?

KEY PYTEST CONCEPTS DEMONSTRATED:
    1. TEST CLASSES       — Group related tests. Class name must start with "Test".
    2. FIXTURE INJECTION  — Name a fixture in the param list; pytest provides it.
    3. ASSERTIONS         — `assert expr` — if False, test fails with a clear diff.
    4. CROSS-CONFTEST     — Tests here use fixtures from BOTH conftest files:
                             - sample_buy_order  → from tests/conftest.py (root)
                             - cancelled_order   → from tests/unit/conftest.py (local)

NAMING CONVENTIONS:
    - File must start with test_ (pytest discovers it)
    - Class must start with Test (pytest discovers it)
    - Methods must start with test_ (pytest discovers them)
    - Non-test helper methods can have any name (e.g., _submit_order)
"""

from src.models.order import Order, Side, OrderType, OrderStatus


class TestOrderCreation:
    """Basic order creation tests using fixtures from root conftest.py.

    WHAT WE'RE TESTING:
        That our conftest fixtures produce orders with the expected field values.
        This seems trivial, but it validates that:
        1. The fixture functions run without errors
        2. The Order dataclass accepts the arguments correctly
        3. The field values match what we expect

    WHY THIS MATTERS:
        If someone changes the fixture (e.g., changes the default symbol),
        these tests will catch it immediately. Fixtures are shared code —
        a bug in a fixture breaks every test that uses it.
    """

    def test_buy_order_has_correct_side(self, sample_buy_order: Order) -> None:
        """Fixture provides a valid BUY order — verify its side.

        HOW FIXTURE INJECTION WORKS HERE:
            1. pytest sees `sample_buy_order` in the parameter list
            2. pytest looks up the fixture named "sample_buy_order"
            3. pytest finds it in tests/conftest.py (root conftest)
            4. pytest calls the fixture function, gets an Order object
            5. pytest passes that Order to this test as `sample_buy_order`

        We NEVER import conftest.py — pytest does it automatically.
        """
        assert sample_buy_order.side == Side.BUY
        # If this fails, pytest shows a clear diff:
        #   AssertionError: assert <Side.SELL: 'SELL'> == <Side.BUY: 'BUY'>

    def test_sell_order_has_correct_symbol(self, sample_sell_order: Order) -> None:
        """Fixture provides a valid SELL order — verify its symbol."""
        assert sample_sell_order.symbol == "AAPL"

    def test_market_order_has_no_price(self, sample_market_order: Order) -> None:
        """Market orders should not require a price.

        This validates the business rule: MARKET orders let the exchange
        decide the price, so the `price` field should be None.
        """
        assert sample_market_order.price is None
        assert sample_market_order.order_type == OrderType.MARKET


class TestOrderProperties:
    """Test computed properties on the Order model.

    WHAT ARE @property METHODS?
        They're methods that look like attributes:
            order.remaining_quantity    (not order.remaining_quantity())
        They compute a value from other fields each time they're accessed.

    WHY TEST PROPERTIES?
        Properties often contain subtle math or logic. Testing them ensures:
        - The formula is correct (quantity - filled_quantity)
        - Edge cases work (0 remaining, fully filled, etc.)
        - The property updates correctly when underlying fields change
    """

    def test_remaining_quantity_new_order(self, sample_buy_order: Order) -> None:
        """A new order has 0 filled, so remaining == total quantity."""
        assert sample_buy_order.remaining_quantity == 100
        # 100 (total) - 0 (filled) = 100 (remaining)

    def test_remaining_quantity_partially_filled(self, sample_buy_order: Order) -> None:
        """After filling 30 shares, 70 should remain.

        NOTE: We mutate the fixture here (set filled_quantity = 30).
        This is SAFE because sample_buy_order has function scope —
        every test gets its OWN fresh Order object.
        If it were session-scoped, this mutation would leak to other tests!
        """
        sample_buy_order.filled_quantity = 30  # Simulate a partial fill
        assert sample_buy_order.remaining_quantity == 70
        # 100 (total) - 30 (filled) = 70 (remaining)

    def test_is_complete_new_order(self, sample_buy_order: Order) -> None:
        """A brand new order is NOT complete (it hasn't been filled yet)."""
        assert sample_buy_order.is_complete is False
        # Status is NEW, which is not in the terminal states set

    def test_is_complete_filled_order(self, sample_buy_order: Order) -> None:
        """After being filled, an order IS complete.

        We manually set status to FILLED to simulate the exchange filling it.
        is_complete checks if status is in {FILLED, CANCELLED, REJECTED}.
        """
        sample_buy_order.status = OrderStatus.FILLED
        assert sample_buy_order.is_complete is True

    def test_is_complete_cancelled_order(self, cancelled_order: Order) -> None:
        """Uses fixture from tests/unit/conftest.py (sub-level).

        CONFTEST HIERARCHY IN ACTION:
            `cancelled_order` is defined in tests/unit/conftest.py.
            It's NOT in the root conftest.py.
            This test is in tests/unit/, so it CAN access it.
            A test in tests/integration/ would get a "fixture not found" error.
        """
        assert cancelled_order.is_complete is True
        # Status is CANCELLED, which IS in the terminal states set


class TestOrderFactory:
    """Test the make_order factory fixture.

    WHAT IS A FACTORY FIXTURE?
        A fixture that returns a FUNCTION instead of an object.
        You call the function with keyword arguments to create customised objects.

    WHY TEST THE FACTORY?
        The factory is a critical shared tool. If it's broken, dozens of tests
        across the project will fail with confusing errors. Testing it directly
        ensures we catch factory bugs immediately.
    """

    def test_factory_default(self, make_order) -> None:
        """With no arguments, factory produces an order with default values."""
        order = make_order()  # Call the factory with no overrides
        assert order.symbol == "AAPL"  # Default symbol
        assert order.quantity == 100    # Default quantity

    def test_factory_custom_symbol(self, make_order) -> None:
        """Factory lets you override specific fields while keeping defaults for the rest."""
        order = make_order(symbol="TSLA", quantity=500)
        assert order.symbol == "TSLA"   # Overridden
        assert order.quantity == 500     # Overridden
        # side, price, order_type still have their defaults

    def test_factory_produces_unique_ids(self, make_order) -> None:
        """Each order from the factory must have a unique ID.

        This validates that default_factory=lambda: str(uuid.uuid4())
        generates a NEW UUID for each Order instance, not a shared one.
        """
        o1 = make_order()
        o2 = make_order()
        assert o1.order_id != o2.order_id
        # UUIDs are 128-bit random numbers — collision probability is ~0


class TestSessionScopedFixture:
    """Verify that session-scoped fixtures behave correctly.

    KEY INSIGHT:
        The db_connection fixture has scope="session", which means:
        - It's created ONCE when the first test needs it
        - ALL tests across ALL files share the SAME dict object
        - It's destroyed only after the last test in the session finishes

        We can verify this by:
        1. Checking the dict has expected keys (test_db_connection_exists)
        2. Incrementing query_count and checking it persists (test_db_connection_tracks_queries)
           If it were function-scoped, query_count would reset to 0 for each test.
    """

    def test_db_connection_exists(self, db_connection: dict) -> None:
        """Verify the simulated connection has the expected structure."""
        assert "host" in db_connection
        assert db_connection["db"] == "test_trading"

    def test_db_connection_tracks_queries(self, db_connection: dict) -> None:
        """Increment query count — proves the fixture persists across tests.

        Because db_connection is session-scoped, this mutation is visible
        to ALL subsequent tests. If another test file also uses db_connection,
        it will see the incremented query_count.
        """
        db_connection["query_count"] += 1
        assert db_connection["query_count"] >= 1

    def test_session_id_is_string(self, test_session_id: str) -> None:
        """Verify the session ID fixture returns a properly formatted string."""
        assert test_session_id.startswith("test-session-")
