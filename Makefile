.PHONY: setup install-backend install-frontend seed backend frontend dev test build check smoke-provider clean

PROVIDER ?= deepseek

setup: install-backend install-frontend

install-backend:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.lock

install-frontend:
	cd frontend && npm ci

seed:
	cd backend && .venv/bin/python seed.py

backend:
	cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1

frontend:
	cd frontend && npm run dev

dev:
	python3 scripts/dev.py

test:
	cd backend && .venv/bin/pytest -q

build:
	cd frontend && npm run build

check: test build
	cd backend && .venv/bin/python -m compileall app seed.py smoke_test_provider.py
	cd frontend && npm audit --audit-level=high

smoke-provider:
	cd backend && .venv/bin/python smoke_test_provider.py --provider $(PROVIDER)

clean:
	@echo "Remove generated .venv, node_modules, dist, and database files manually if needed."
