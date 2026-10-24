import pytest

from shopcart import Cart


def test_lowercase_code_accepted():
    cart = Cart()
    cart.add("A", 100.0)
    cart.apply_discount("save10")
    assert cart.total() == pytest.approx(108.0)


def test_code_with_spaces_accepted():
    cart = Cart()
    cart.add("A", 100.0)
    cart.apply_discount("  SAVE25 ")
    assert cart.total() == pytest.approx(90.0)


def test_unknown_code_still_raises():
    with pytest.raises(ValueError):
        Cart().apply_discount("save99")
