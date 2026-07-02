VENV ?= .venv
TRCR_REPO_ROOT ?= $(CURDIR)
COMPOSE_FILE ?= $(TRCR_REPO_ROOT)/deployment/docker-compose.yml
COMPOSE_ENV_FILE ?= $(TRCR_REPO_ROOT)/deployment/.env
COMPOSE_FILE_PATH := $(abspath $(COMPOSE_FILE))
COMPOSE_ENV_PATH := $(abspath $(COMPOSE_ENV_FILE))
COMPOSE_ENV_ARG := $(if $(wildcard $(COMPOSE_ENV_PATH)),--env-file $(COMPOSE_ENV_PATH),)
COMPOSE ?= TRCR_REPO_ROOT="$(TRCR_REPO_ROOT)" docker compose $(COMPOSE_ENV_ARG) -f $(COMPOSE_FILE_PATH)

ifeq ($(OS),Windows_NT)
DETECTED_OS := windows
PYTHON ?= py -3
VENV_PYTHON := $(VENV)/Scripts/python.exe
else
UNAME_S := $(shell uname -s 2>/dev/null)
ifeq ($(UNAME_S),Linux)
DETECTED_OS := linux
else
DETECTED_OS := unsupported
endif
PYTHON ?= python3
VENV_PYTHON := $(VENV)/bin/python
endif

TCR=python .agents/skills/truecrime-cult-research/scripts/tcr.py

.PHONY: check-os install install-minimum install-linux install-windows docker-build docker-up docker-down docker-logs docker-shell docker-pull-model docker-smoke docker-config check init-sample validate-sample export-sample

check-os:
	@echo "Detected OS: $(DETECTED_OS)"

install: install-minimum

install-minimum:
ifeq ($(DETECTED_OS),linux)
	$(MAKE) install-linux
else ifeq ($(DETECTED_OS),windows)
	$(MAKE) install-windows
else
	@echo "Unsupported OS for install-minimum: $(UNAME_S)"
	@echo "Supported install targets are Linux and Windows."
	@exit 1
endif

install-linux:
ifneq ($(DETECTED_OS),linux)
	@echo "install-linux requires Linux; detected $(DETECTED_OS)."
	@exit 1
else
	$(PYTHON) -c "import sys; raise SystemExit('Python 3.10+ required') if sys.version_info < (3, 10) else None"
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e .
endif

install-windows:
ifneq ($(DETECTED_OS),windows)
	@echo "install-windows requires Windows; detected $(DETECTED_OS)."
	@exit 1
else
	$(PYTHON) -c "import sys; raise SystemExit('Python 3.10+ required') if sys.version_info < (3, 10) else None"
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e .
endif

docker-config:
	$(COMPOSE) config

docker-build:
	$(COMPOSE) build trcr

docker-up:
	$(COMPOSE) up -d

docker-down:
	$(COMPOSE) down

docker-logs:
	$(COMPOSE) logs -f

docker-shell:
	$(COMPOSE) exec trcr /bin/bash

docker-pull-model:
	$(COMPOSE) exec trcr deployment/scripts/bootstrap-ollama.sh

docker-smoke:
	$(COMPOSE) exec trcr deployment/scripts/smoke-test.sh

check:
	python -m compileall src/case_builder .agents/skills/truecrime-cult-research/scripts
	$(TCR) validate data/examples/synthetic_case

init-sample:
	$(TCR) init-case data/cases/sample_case --title "Sample Case"

validate-sample:
	$(TCR) validate data/cases/sample_case

export-sample:
	$(TCR) export-manim data/cases/sample_case
	$(TCR) report data/cases/sample_case
