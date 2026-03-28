"""Tests for the order validator — parametrized across multiple input cases.

WHAT IS @pytest.mark.parametrize?
    It runs the SAME test function multiple times with DIFFERENT inputs.
    Instead of writing 5 separate test functions (one per case), we write
    ONE function and pass it a table of inputs + expected results.

    This is like a truth table:
        INPUT (symbol, qty, price, ...)  →  EXPECTED RESULT (error field or None)

    pytest generates a separate test for each row in the table.
    In CI output you'll see:
        test_order_validation_cases[valid_order]         PASSED
        test_order_validation_cases[zero_quantity]        PASSED
        test_order_validation_cases[negative_price]       PASSED
        test_order_validation_cases[missing_symbol]       PASSED
        test_order_validation_cases[oversized_quantity]   PASSED

    The [names] come from the `ids=` parameter.

WHAT IS @pytest.mark.smoke / regression / slow?
    Custom MARKS that let you tag tests and run subsets:
        make smoke       → runs only @pytest.mark.smoke tests (~2 sec)
        make regression  → runs only @pytest.mark.regression tests
        make test -m "not slow"  → skips slow tests

    Marks are registered in pyproject.toml under [tool.pytest.ini_options].markers
    to avoid typo warnings (--strict-markers mode).

WHAT IS pytest.raises?
    A context manager that asserts a specific exception is raised:
        with pytest.raises(ValidationError) as exc_info:
            validate_order(bad_order)
        assert exc_info.value.field == "quantity"

    If the code does NOT raise, the test FAILS.
    If it raises a DIFFERENT exception, the test FAILS.
    If it raises the RIGHT exception, we can inspect it via exc_info.value.

THIS FILE COVERS: Week 1 Day 4 of the roadmap.
"""

from __future__ import annotations  # Allows "str | None" syntax on Python 3.9

import pytest

from src.models.order import Order, Side, OrderType
from src.validators.order_validator import validate_order, ValidationError


class TestValidateOrder:
    """Parametrized validation tests.

    STRUCTURE:
        1. One smoke test     — quick sanity check that a valid order passes
        2. Parametrized test  — 5 cases covering valid + 4 types of invalid
        3. Regression tests   — specific bugs that were (or could be) introduced
        4. Slow test          — bulk validation (heavier, takes longer)
    """

    @pytest.mark.smoke
    def test_valid_limit_order(self, sample_buy_order: Order) -> None:
        """A well-formed order passes validation.

        @pytest.mark.smoke means this runs in the fast "smoke test" suite.
        Smoke tests are the first thing CI runs — if these fail, everything
        else is likely broken too, so we fail fast.
        """
        assert validate_order(sample_buy_order) is True

    # ─── THE PARAMETRIZED TEST ───────────────────────────────────────────
    # @pytest.mark.parametrize takes:
    #   1. A comma-separated string of parameter names
    #   2. A list of tuples — each tuple is one test case
    #   3. ids= — human-readable names for each case (shown in output)
    @pytest.mark.parametrize(
        "symbol, side, qty, price, order_type, expected_error_field",
        [
            # CASE 1: Valid order — all fields correct, should NOT raise any exception.
            # expected_error_field is None, meaning we expect success.
            ("AAPL", Side.BUY, 100, 150.0, OrderType.LIMIT, None),

            # CASE 2: Zero quantity — you can't buy 0 shares.
            # Validator should raise ValidationError with field="quantity".
            ("AAPL", Side.BUY, 0, 150.0, OrderType.LIMIT, "quantity"),

            # CASE 3: Negative price — $-10.00 makes no sense.
            # Validator should raise ValidationError with field="price".
            ("AAPL", Side.SELL, 100, -10.0, OrderType.LIMIT, "price"),

            # CASE 4: Missing symbol — empty string "" is not a valid ticker.
            # Validator should raise ValidationError with field="symbol".
            ("", Side.BUY, 100, 150.0, OrderType.LIMIT, "symbol"),

            # CASE 5: Oversized quantity — 2 million shares exceeds MAX_QUANTITY (1 million).
            # This is a "fat finger" check. Validator should raise with field="quantity".
            ("MSFT", Side.BUY, 2_000_000, 300.0, OrderType.LIMIT, "quantity"),
        ],
        # ids= provides human-readable names that appear in test output.
        # Without ids, pytest would show the raw tuple values (ugly).
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
        """Parametrized test covering 5 distinct validation scenarios.

        HOW THIS WORKS:
            pytest calls this function 5 times (once per tuple in the list above).
            Each call gets different values for symbol, side, qty, etc.
            The test creates an Order with those values, then:
              - If expected_error_field is None → validate should succeed
              - If expected_error_field is "quantity" → validate should raise
                ValidationError with .field == "quantity"
        """
        # Create an Order with the parametrized values
        order = Order(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price,
            order_type=order_type,
        )

        if expected_error_field is None:
            # ✅ This case should pass validation without raising
            assert validate_order(order) is True
        else:
            # ❌ This case should RAISE a ValidationError.
            # pytest.raises catches the exception and stores it in exc_info.
            with pytest.raises(ValidationError) as exc_info:
                validate_order(order)
            # Verify the error is about the RIGHT field
            # (not just "some" ValidationError)
            assert exc_info.value.field == expected_error_field

    # ─── REGRESSION TESTS ─────────────────────────────────────────────
    # Regression tests guard against specific bugs that were found (or could be).
    # @pytest.mark.regression lets us run just these: `make regression`

    @pytest.mark.regression
    def test_market_order_without_price_is_valid(self) -> None:
        """MARKET orders don't need a price — this must NOT be rejected.

        WHY IS THIS A REGRESSION TEST?
            Imagine someone tightens the validator to require price for ALL orders.
            This test would catch that immediately. It guards the rule:
            "MARKET orders can have price=None."
        """
        order = Order(
            symbol="GOOGL",
            side=Side.BUY,
            quantity=100,
            order_type=OrderType.MARKET,  # No price needed
        )
        assert validate_order(order) is True

    @pytest.mark.regression
    def test_limit_order_without_price_is_rejected(self) -> None:
        """LIMIT orders MUST have a price — omitting it must be rejected.

        This is the counterpart to the above test. Together they verify:
            MARKET + no price = ✅  (test above)
            LIMIT  + no price = ❌  (this test)
        """
        order = Order(
            symbol="AAPL",
            side=Side.BUY,
            quantity=100,
            price=None,              # ← Missing price!
            order_type=OrderType.LIMIT,  # ← But order type requires one!
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_order(order)
        assert exc_info.value.field == "price"

    @pytest.mark.regression
    def test_unknown_symbol_is_rejected(self) -> None:
        """Symbols not in the valid set must be rejected.

        In a real system, trying to trade a non-existent symbol would
        cause downstream failures. Better to catch it at validation time.
        """
        order = Order(
            symbol="FAKESYM",  # ← Not in VALID_SYMBOLS set
            side=Side.BUY,
            quantity=100,
            price=50.0,
            order_type=OrderType.LIMIT,
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_order(order)
        assert exc_info.value.field == "symbol"

    # ─── SLOW TEST ─────────────────────────────────────────────────
    # @pytest.mark.slow lets us exclude this from quick runs:
    #   pytest -m "not slow"   (skips slow tests)
    #   make slow              (runs ONLY slow tests)

    @pytest.mark.slow
    def test_bulk_validation(self, bulk_orders) -> None:
        """Validate a batch of 10 orders (uses unit conftest fixture).

        This uses the `bulk_orders` fixture from tests/unit/conftest.py.
        That fixture creates 10 diverse orders using the `make_order` factory.

        WHY BULK TEST?
            - Validates the factory produces valid orders
            - Catches edge cases in diverse combinations (different symbols, quantities, sides)
            - In production, you'd run this with 10,000+ orders for confidence
        """
        for order in bulk_orders:
            assert validate_order(order) is True
