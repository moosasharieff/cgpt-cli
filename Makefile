# -------- cgpt-cli deps workflow (pip-tools) --------
# Usage:
#   make venv          # create .venv and install pip-tools
#   make compile       # build requirements.txt + requirements_dev.txt (with hashes)
#   make install       # install runtime deps exactly (hash-checked)
#   make install-dev   # install dev deps exactly (hash-checked)
#   make upgrade PKG=requests   # bump one base package
#   make upgrade-all            # bump all base packages
#   make format qa / lint / type / test / cov / format
#   make show / clean / nuke / activate
# ----------------------------------------------------

.DEFAULT_GOAL := help

PY ?= python3.11
VENV ?= .venv

ifeq ($(OS),Windows_NT)
  VENV_BIN := $(VENV)/Scripts
else
  VENV_BIN := $(VENV)/bin
endif

PYTHON      := $(VENV_BIN)/python
PIP         := $(VENV_BIN)/pip
PIP_COMPILE := $(VENV_BIN)/pip-compile
PIP_SYNC    := $(VENV_BIN)/pip-sync
BLACK       := $(VENV_BIN)/black
RUFF        := $(VENV_BIN)/ruff
MYPY        := $(VENV_BIN)/mypy
PYTEST      := $(VENV_BIN)/pytest

# Add directories to apply linting
PY_SRC := src tests

REQ_BASE_IN   := requirements.in
REQ_BASE_TXT  := requirements.txt
REQ_DEV_IN    := requirements_dev.in
REQ_DEV_TXT   := requirements_dev.txt

.PHONY: help venv compile compile-base compile-dev install install-dev \
        upgrade upgrade-all show clean nuke activate \
        format lint lint-fix type test cov qa

help: ## Show this help
	@echo
	@echo "Commands:"
	@grep -E '^[a-zA-Z0-9_.-]+:.*##' $(MAKEFILE_LIST) | \
	  sed -E 's/^([a-zA-Z0-9_.-]+):.*##[[:space:]]*(.*)/  \1\t\2/'

venv: ## Create .venv and install pip-tools
	@test -d "$(VENV)" || $(PY) -m venv "$(VENV)"
	$(PYTHON) -m pip install -U pip pip-tools

compile: venv ## Compile base and dev lockfiles with hashes
	$(PIP_COMPILE) --generate-hashes $(REQ_BASE_IN)
	$(PIP_COMPILE) --generate-hashes $(REQ_DEV_IN)

compile-base: venv ## Compile only base lockfile
	$(PIP_COMPILE) --generate-hashes $(REQ_BASE_IN)

compile-dev: venv ## Compile only dev lockfile
	$(PIP_COMPILE) --generate-hashes $(REQ_DEV_IN)

install: venv ## Install exact runtime env (prod/CI)
	$(PIP_SYNC) $(REQ_BASE_TXT) --pip-args="--require-hashes"

install-dev: venv ## Install exact local dev env
	$(PIP_SYNC) $(REQ_DEV_TXT) --pip-args="--require-hashes"

upgrade: venv ## Upgrade one base package: make upgrade PKG=requests
	@test -n "$(PKG)" || (echo "Usage: make upgrade PKG=<package>"; exit 2)
	$(PIP_COMPILE) --upgrade-package $(PKG) --generate-hashes $(REQ_BASE_IN)
	$(PIP_COMPILE) --generate-hashes $(REQ_DEV_IN)

upgrade-all: venv ## Upgrade all base deps (then refresh dev)
	$(PIP_COMPILE) --upgrade --generate-hashes $(REQ_BASE_IN)
	$(PIP_COMPILE) --generate-hashes $(REQ_DEV_IN)

# ---------- Quality targets (require dev tools installed) ----------
format: ## Format code with Black
	$(BLACK) $(PY_SRC)

lint: ## Run Ruff lint (no changes)
	$(RUFF) check $(PY_SRC)

lint-fix: ## Run Ruff auto-fix then Black format
	$(RUFF) check --fix $(PY_SRC)
	$(BLACK) $(PY_SRC)

type: ## Static type-check with MyPy
	$(MYPY) $(PY_SRC)

test: ## Run test suite with pytest
	$(PYTEST)

cov: ## Run tests with coverage report
	$(PYTEST) --cov=$(PKG) --cov-report=term-missing

qa: ## Run full quality gate (lint, type, tests)
	$(RUFF) check $(PY_SRC)
	$(MYPY) $(PY_SRC)
	$(PYTEST)

# ---------- Misc ----------
show: venv ## Print Python/pip/pip-tools versions inside .venv
	$(PYTHON) -V
	$(PIP) -V
	$(PIP_COMPILE) --version || true

clean: ## Remove lockfiles (keeps .in files)
	rm -f $(REQ_BASE_TXT) $(REQ_DEV_TXT)

nuke: ## Remove the virtualenv
	rm -rf "$(VENV)"

activate: ## Print how to activate the venv
	@echo "Unix/macOS:  source $(VENV_BIN)/activate"
	@echo "Windows:     .\\$(VENV)\\Scripts\\activate"
