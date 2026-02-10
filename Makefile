.PHONY: dev test lint migrate deploy-mac

dev:
	uvicorn app.main:app --reload --port 8000

test:
	pytest

lint:
	ruff check . && ruff format --check .

migrate:
	alembic upgrade head

deploy-mac:
	bash scripts/deploy.sh
