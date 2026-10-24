import pytest

from shopcart import Cart


def test_ten_units_get_bulk_price():
    cart = Cart()
    cart.add("A", 2.0, 10)
    assert cart.subtotal() == pytest.approx(19.0)


def test_nine_units_full_price():
    cart = Cart()
    cart.add("A", 2.0, 9)
    assert cart.subtotal() == pytest.approx(18.0)


def test_bulk_applies_per_line():
    cart = Cart()
    cart.add("A", 1.0, 20)
    cart.add("B", 1.0, 5)
    assert cart.subtotal() == pytest.approx(19.0 + 5.0)
