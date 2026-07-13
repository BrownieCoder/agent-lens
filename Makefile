.PHONY: setup install-backend install-frontend seed backend frontend dev test build check smoke-provider clean

PROVIDER ?= deepseek

setup: install-backend install-frontend

install-backend:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

install-frontend:
	cd frontend && npm ci

seed:
	cd backend && .venv/bin/python seed.py

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

dev:
	@trap 'kill 0' INT TERM EXIT; \
	(cd backend && .venv/bin/uvicorn app.main:app --reload) & \
	(cd frontend && npm run dev) & \
	wait

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
