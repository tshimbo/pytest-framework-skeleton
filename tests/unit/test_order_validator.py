"""Tests for the order validator — parametrized across multiple input cases.

This covers Week 1 Day 4: parametrize across 5 input cases.
"""

from __future__ import annotations

import pytest

from src.models.order import Order, Side, OrderType
from src.validators.order_validator import validate_order, ValidationError


class TestValidateOrder:
    """Parametrized validation tests."""

    @pytest.mark.smoke
    def test_valid_limit_order(self, sample_buy_order: Order) -> None:
        """A well-formed order passes validation."""
        assert validate_order(sample_buy_order) is True

    @pytest.mark.parametrize(
        "symbol, side, qty, price, order_type, expected_error_field",
        [
            # Case 1: Valid order — should NOT raise
            ("AAPL", Side.BUY, 100, 150.0, OrderType.LIMIT, None),
            # Case 2: Zero quantity
            ("AAPL", Side.BUY, 0, 150.0, OrderType.LIMIT, "quantity"),
            # Case 3: Negative price
            ("AAPL", Side.SELL, 100, -10.0, OrderType.LIMIT, "price"),
            # Case 4: Missing symbol (empty string)
            ("", Side.BUY, 100, 150.0, OrderType.LIMIT, "symbol"),
            # Case 5: Oversized quantity
            ("MSFT", Side.BUY, 2_000_000, 300.0, OrderType.LIMIT, "quantity"),
        ],
        ids=[
            "valid_order",
            "zero_quantity",
            "negative_price",
            "missing_symbol",
            "oversized_quantity",
        ],
    )
    def test_order_validation_cases(
        self,
        symbol: str,
        side: Side,
        qty: int,
        price: float,
        order_type: OrderType,
        expected_error_field: "str | None",
    ) -> None:
        """Parametrized test covering 5 distinct validation scenarios."""
        order = Order(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price,
            order_type=order_type,
        )
        if expected_error_field is None:
            assert validate_order(order) is True
        else:
            with pytest.raises(ValidationError) as exc_info:
                validate_order(order)
            assert exc_info.value.field == expected_error_field

    @pytest.mark.regression
    def test_market_order_without_price_is_valid(self) -> None:
        """Market orders don't need a price — regression case."""
        order = Order(
            symbol="GOOGL",
            side=Side.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
        )
        assert validate_order(order) is True

    @pytest.mark.regression
    def test_limit_order_without_price_is_rejected(self) -> None:
        """LIMIT order with no price must be rejected."""
        order = Order(
            symbol="AAPL",
            side=Side.BUY,
            quantity=100,
            price=None,
            order_type=OrderType.LIMIT,
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_order(order)
        assert exc_info.value.field == "price"

    @pytest.mark.regression
    def test_unknown_symbol_is_rejected(self) -> None:
        """Symbols not in the valid set must be rejected."""
        order = Order(
            symbol="FAKESYM",
            side=Side.BUY,
            quantity=100,
            price=50.0,
            order_type=OrderType.LIMIT,
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_order(order)
        assert exc_info.value.field == "symbol"

    @pytest.mark.slow
    def test_bulk_validation(self, bulk_orders) -> None:
        """Validate a batch of 10 orders (uses unit conftest fixture)."""
        for order in bulk_orders:
            assert validate_order(order) is True
