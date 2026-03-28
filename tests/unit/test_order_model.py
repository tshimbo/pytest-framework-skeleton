"""Tests for the Order model using shared fixtures from conftest hierarchy."""

import pytest
from src.models.order import Order, Side, OrderType, OrderStatus


class TestOrderCreation:
    """Basic order creation tests using fixtures from root conftest.py."""

    def test_buy_order_has_correct_side(self, sample_buy_order: Order) -> None:
        """Fixture provides a valid BUY order — verify its side."""
        assert sample_buy_order.side == Side.BUY

    def test_sell_order_has_correct_symbol(self, sample_sell_order: Order) -> None:
        """Fixture provides a valid SELL order — verify its symbol."""
        assert sample_sell_order.symbol == "AAPL"

    def test_market_order_has_no_price(self, sample_market_order: Order) -> None:
        """Market orders should not require a price."""
        assert sample_market_order.price is None
        assert sample_market_order.order_type == OrderType.MARKET


class TestOrderProperties:
    """Test computed properties on the Order model."""

    def test_remaining_quantity_new_order(self, sample_buy_order: Order) -> None:
        assert sample_buy_order.remaining_quantity == 100

    def test_remaining_quantity_partially_filled(self, sample_buy_order: Order) -> None:
        sample_buy_order.filled_quantity = 30
        assert sample_buy_order.remaining_quantity == 70

    def test_is_complete_new_order(self, sample_buy_order: Order) -> None:
        assert sample_buy_order.is_complete is False

    def test_is_complete_filled_order(self, sample_buy_order: Order) -> None:
        sample_buy_order.status = OrderStatus.FILLED
        assert sample_buy_order.is_complete is True

    def test_is_complete_cancelled_order(self, cancelled_order: Order) -> None:
        """Uses fixture from tests/unit/conftest.py (sub-level)."""
        assert cancelled_order.is_complete is True


class TestOrderFactory:
    """Test the make_order factory fixture."""

    def test_factory_default(self, make_order) -> None:
        order = make_order()
        assert order.symbol == "AAPL"
        assert order.quantity == 100

    def test_factory_custom_symbol(self, make_order) -> None:
        order = make_order(symbol="TSLA", quantity=500)
        assert order.symbol == "TSLA"
        assert order.quantity == 500

    def test_factory_produces_unique_ids(self, make_order) -> None:
        o1 = make_order()
        o2 = make_order()
        assert o1.order_id != o2.order_id


class TestSessionScopedFixture:
    """Verify that session-scoped fixtures behave correctly."""

    def test_db_connection_exists(self, db_connection: dict) -> None:
        assert "host" in db_connection
        assert db_connection["db"] == "test_trading"

    def test_db_connection_tracks_queries(self, db_connection: dict) -> None:
        db_connection["query_count"] += 1
        assert db_connection["query_count"] >= 1

    def test_session_id_is_string(self, test_session_id: str) -> None:
        assert test_session_id.startswith("test-session-")
