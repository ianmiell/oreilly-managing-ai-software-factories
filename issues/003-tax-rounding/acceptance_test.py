from shopcart import Cart


def test_no_float_noise():
    cart = Cart()
    cart.add("A", 0.10, 3)
    assert cart.tax() == 0.06
    assert cart.total() == 0.36


def test_rounded_with_discount():
    cart = Cart()
    cart.add("A", 19.99)
    cart.apply_discount("SAVE10")
    assert cart.tax() == 3.6
    assert cart.total() == 21.59


def test_still_returns_float():
    cart = Cart()
    cart.add("A", 1.0)
    assert isinstance(cart.total(), float)
