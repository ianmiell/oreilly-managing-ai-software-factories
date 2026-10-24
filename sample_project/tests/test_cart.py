import pytest

from shopcart import Cart


def test_subtotal():
    cart = Cart()
    cart.add("A", 10.0, 2)
    cart.add("B", 5.0)
    assert cart.subtotal() == 25.0


def test_discount_and_tax():
    cart = Cart()
    cart.add("A", 100.0)
    cart.apply_discount("SAVE10")
    assert cart.total() == 108.0


def test_unknown_code_raises():
    with pytest.raises(ValueError):
        Cart().apply_discount("NOPE")


def test_qty_must_be_positive():
    with pytest.raises(ValueError):
        Cart().add("A", 1.0, 0)
