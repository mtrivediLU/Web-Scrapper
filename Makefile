.PHONY: install demo api test lint typecheck check

install:
	python -m pip install -e ".[dev]"

demo:
	web-scraper scrape --config configs/faculty.yaml --output outputs/faculty.xlsx

api:
	web-scraper api --config configs/api.yaml --output outputs/faculty.csv

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy src

check: test lint typecheck

