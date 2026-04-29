PYTHON=python3
VENV_DIR=venv
PIP=$(VENV_DIR)/bin/pip
UVICORN=$(VENV_DIR)/bin/uvicorn

.PHONY: install start db stop local

install:
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

start: db
	docker compose up --build

db:
	docker compose up -d db

stop:
	docker compose down

local: install
	$(UVICORN) app.server:app --reload --host 0.0.0.0 --port 8000
