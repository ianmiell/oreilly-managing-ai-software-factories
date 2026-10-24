# Conventions for agents working on shopcart

- Python 3.11+. Do not add dependencies.
- The public API (`subtotal`, `tax`, `total`) returns floats. Do not change return types.
- Never modify or delete existing tests. Add new tests in new files under `tests/`.
- Keep changes minimal and focused on the issue. No drive-by refactors.
- Constants go at the top of `cart.py` in UPPER_CASE.
- Run `python -m pytest -q` and `python -m ruff check .` before finishing.
