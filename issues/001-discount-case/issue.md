# Discount codes should ignore case and surrounding spaces

Customers type codes like `save10` or ` SAVE25 ` and get "unknown discount code".
`apply_discount` should accept codes regardless of case and leading/trailing
whitespace. Unknown codes must still raise `ValueError`.
