.PHONY: test lint format check
test:
	.venv/bin/pytest -m "not smoke"
lint:
	.venv/bin/ruff check .
format:
	.venv/bin/ruff format .
check: test lint format pyright
pyright:
	.venv/bin/pyright
