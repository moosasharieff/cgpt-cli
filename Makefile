# -------- cgpt-cli deps workflow (pip-tools) --------

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
COV_TARGET ?= $(firstword $(filter src/cgpt_cli cgpt_cli,$(FOUND_SRC)))
COV_TARGET := $(if $(COV_TARGET),$(COV_TARGET),.)

REQ_BASE_IN   := requirements.in
REQ_BASE_TXT  := requirements.txt
REQ_DEV_IN    := requirements_dev.in
REQ_DEV_TXT   := requirements_dev.txt

# -------- act (GitHub Actions locally) --------
# Requires Docker + act. Apple Silicon defaults to linux/amd64.
ACT ?= act
ACT_WORKFLOW ?= .github/workflows/deps-lock-check.yml
ACT_IMAGE ?= ghcr.io/catthehacker/ubuntu:act-22.04
ACT_PLATFORM ?= ubuntu-latest=$(ACT_IMAGE)
UNAME_M := $(shell uname -m)
ifeq ($(UNAME_M),arm64)
  ACT_ARCH_FLAG ?= --container-architecture linux/amd64
endif
ACT_EXTRA_FLAGS ?=

.PHONY: help venv compile compile-base compile-dev install install-dev \
        upgrade upgrade-all show clean nuke activate \
        format lint lint-fix type test cov qa check-src \
        act-pr act-push act-lockcheck act-smoke act-list act-pr-debug \
        sanity-check sanity-clean \
        pre-commit-run pre-commit-update pre-commit-ci

help: ## Show this help
	@echo
	@echo "Commands:"
	@awk -F':.*##' '/^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

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

# ---------- Quality targets ----------
format: ## Format code with Black
	$(BLACK) $(PY_SRC)

lint: ## Ruff lint (no changes)
	$(RUFF) check $(PY_SRC)

lint-fix: ## Ruff auto-fix, then Black format
	$(RUFF) check --fix $(PY_SRC)
	$(BLACK) $(PY_SRC)

type: ## MyPy static type-check
	$(MYPY) $(PY_SRC)

test: ## Run tests
	$(PIP) install -e .
	$(PYTEST) -qv

cov: ## Tests with coverage report
	$(PYTEST) --cov=$(COV_TARGET) --cov-report=term-missing

qa: ## Full quality gate (lint, type)
	$(RUFF) check $(PY_SRC)
	$(MYPY) $(PY_SRC)


# ---------- act helpers ----------
act-pr-dlc: ## Run deps-lock-check (pull_request) locally with act
	$(ACT) pull_request -W $(ACT_WORKFLOW) -P $(ACT_PLATFORM) $(ACT_ARCH_FLAG) --bind $(ACT_EXTRA_FLAGS)

act-push-dlc: ## Run deps-lock-check (push) locally with act
	$(ACT) push -W $(ACT_WORKFLOW) -P $(ACT_PLATFORM) $(ACT_ARCH_FLAG) --bind $(ACT_EXTRA_FLAGS)

act-dlc-lockcheck: ## Run only 'lockcheck' job (pull_request) via act
	$(ACT) pull_request -W $(ACT_WORKFLOW) -j lockcheck -P $(ACT_PLATFORM) $(ACT_ARCH_FLAG) --bind $(ACT_EXTRA_FLAGS)

act-dlc-smoke: ## Run only 'smoke-install' job (pull_request) via act
	$(ACT) pull_request -W $(ACT_WORKFLOW) -j smoke-install -P $(ACT_PLATFORM) $(ACT_ARCH_FLAG) --bind $(ACT_EXTRA_FLAGS)

act-dlc-list: ## List jobs detected in $(ACT_WORKFLOW)
	$(ACT) -l -W $(ACT_WORKFLOW)

act-pr-dlc-debug: ## Run deps-lock-check (pull_request) via act with debug + reuse
	$(ACT) pull_request -W $(ACT_WORKFLOW) -P $(ACT_PLATFORM) $(ACT_ARCH_FLAG) --bind -r --secret ACTIONS_STEP_DEBUG=true $(ACT_EXTRA_FLAGS)

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


# ---------- Packaging & Distributing ----------
sanity-check: venv ## Build sdist/wheel and verify CLI works
	$(PIP) install -U pip build
	$(PIP) install -e .
	# Ensure the console script is available and prints help
	$(VENV_BIN)/cgpt --help >/dev/null
	# Build distribution artifacts
	$(PYTHON) -m build
	# Verify artifacts exist
	@ls dist/*.whl >/dev/null 2>&1 || (echo "❌ wheel not found in dist/"; exit 1)
	@ls dist/*.tar.gz >/dev/null 2>&1 || (echo "❌ sdist (.tar.gz) not found in dist/"; exit 1)
	@echo "✅ Sanity check passed: CLI runs and artifacts built (wheel + sdist)."

sanity-clean: ## Remove build artifacts (dist/, build/, *.egg-info)
	rm -rf dist build *.egg-info

# ------------- Pre-commit ---------------
pre-commit-run: ## Run pre-commit on all files
	$(VENV_BIN)/pre-commit run --all-files

pre-commit-update: ## Autoupdate hook revisions
	$(VENV_BIN)/pre-commit autoupdate

pre-commit-ci: ## Run hooks in CI mode (fails on issues)
	$(VENV_BIN)/pre-commit run --all-files --show-diff-on-failure --color=always
