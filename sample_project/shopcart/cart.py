"""A tiny shopping cart: the demo target for the software factory."""

from dataclasses import dataclass, field

DISCOUNT_CODES = {"SAVE10": 0.10, "SAVE25": 0.25}
TAX_RATE = 0.2


@dataclass
class LineItem:
    sku: str
    unit_price: float
    qty: int


@dataclass
class Cart:
    items: list[LineItem] = field(default_factory=list)
    discount: float = 0.0

    def add(self, sku: str, unit_price: float, qty: int = 1) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        self.items.append(LineItem(sku, unit_price, qty))

    def subtotal(self) -> float:
        return sum(item.unit_price * item.qty for item in self.items)

    def apply_discount(self, code: str) -> None:
        if code not in DISCOUNT_CODES:
            raise ValueError(f"unknown discount code: {code}")
        self.discount = DISCOUNT_CODES[code]

    def _discounted(self) -> float:
        return self.subtotal() * (1 - self.discount)

    def tax(self) -> float:
        return self._discounted() * TAX_RATE

    def total(self) -> float:
        return self._discounted() + self.tax()
