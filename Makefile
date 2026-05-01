PYTHON=python3
VENV_DIR=venv
PIP=$(VENV_DIR)/bin/pip
UVICORN=$(VENV_DIR)/bin/uvicorn
PYTEST=$(VENV_DIR)/bin/pytest
RUFF=$(VENV_DIR)/bin/ruff

.PHONY: install start db test_db stop local local-soft format lint lint-fix test check

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

local: install
	$(UVICORN) app.server:app --reload --host 0.0.0.0 --port 8000

local-soft:
	$(UVICORN) app.server:app --reload --host 0.0.0.0 --port 8000

format:
	$(RUFF) format app tests

lint:
	$(RUFF) check app tests

lint-fix:
	$(RUFF) check app tests --fix

test:
	$(PYTEST)

check: lint test
