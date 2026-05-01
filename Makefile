PYTHON=python3
VENV_DIR=venv
PIP=$(VENV_DIR)/bin/pip
UVICORN=$(VENV_DIR)/bin/uvicorn
PYTEST=$(VENV_DIR)/bin/pytest
RUFF=$(VENV_DIR)/bin/ruff
ALEMBIC=$(VENV_DIR)/bin/alembic

.PHONY: install start db test_db stop local local-soft migrate revision seed format lint lint-fix test coverage check frontend-install frontend dev

install:
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

start: db
	docker compose up --build

db:
	docker compose up -d db redis

test_db:
	docker compose up -d test_db redis

stop:
	docker compose down

local: install migrate
	$(UVICORN) app.server:app --reload --host 0.0.0.0 --port 8000

local-soft: migrate
	$(UVICORN) app.server:app --reload --host 0.0.0.0 --port 8000

migrate:
	$(ALEMBIC) upgrade head

revision:
	$(ALEMBIC) revision --autogenerate -m "$(m)"

seed: migrate
	$(VENV_DIR)/bin/python scripts/seed_dev.py

format:
	$(RUFF) format app tests alembic scripts

lint:
	$(RUFF) check app tests alembic scripts

lint-fix:
	$(RUFF) check app tests alembic scripts --fix

test:
	$(PYTEST)

coverage:
	$(PYTEST) --cov=app --cov-report=term-missing

frontend-install:
	npm --prefix frontend ci

frontend:
	npm --prefix frontend run dev

dev:
	$(UVICORN) app.server:app --reload --host 0.0.0.0 --port 8000 & npm --prefix frontend run dev

check: lint test
