# Tax and totals show floating-point noise

A cart with three items at 0.10 shows tax as 0.06000000000000001.
`tax()` and `total()` must return amounts rounded to 2 decimal places,
rounding half up as our accountants require (for example 0.125 -> 0.13).
Both must keep returning floats.
