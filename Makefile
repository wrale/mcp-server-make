# Project Configuration
.DEFAULT_GOAL := help

# Project settings
PROJECT_NAME = mcp-server-make
PACKAGE_NAME = mcp_server_make
PYTHON_VERSION = 3.12

# Tool configuration
PYTHON = python$(PYTHON_VERSION)
UV = uv
PIP = $(UV) pip
PYTEST = $(VENV_BIN)/pytest
RUFF = $(VENV_BIN)/ruff
MYPY = $(VENV_BIN)/mypy

# Directory structure
SRC_DIR = src
TESTS_DIR = tests
BUILD_DIR = build
DIST_DIR = dist

# OS specific commands and configurations
PASTE_BUFFER := $(HOME)/.makefile_buffer
PBCOPY := $(shell command -v pbcopy 2> /dev/null)
ifeq ($(PBCOPY),)
    COPY_TO_CLIPBOARD = tee $(PASTE_BUFFER)
else
    COPY_TO_CLIPBOARD = tee $(PASTE_BUFFER) && cat $(PASTE_BUFFER) | pbcopy
endif

# Virtual environment
VENV_DIR = .venv
VENV_BIN = $(VENV_DIR)/bin
VENV_PYTHON = $(VENV_BIN)/python

.PHONY: all clean test lint format check deps build install publish help
.PHONY: venv dev-setup x y z r

help: ## Display available commands
	@echo "Available Commands:"
	@echo
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

venv: ## Create virtual environment
	test -d $(VENV_DIR) || $(UV) venv
	$(UV) pip install -e .

dev-setup: venv ## Set up development environment
	$(UV) pip install --upgrade pip
	$(UV) pip install -e ".[dev]"

clean: ## Clean build artifacts
	rm -rf $(BUILD_DIR) $(DIST_DIR) .pytest_cache .ruff_cache .mypy_cache *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +

deps: ## Install and verify dependencies
	$(UV) pip install -e .
	$(UV) pip sync

format: ## Format code
	$(RUFF) format .
	$(RUFF) check --fix .

lint: ## Run linters
	$(RUFF) check .
	$(MYPY) $(SRC_DIR)/$(PACKAGE_NAME)

test: ## Run tests
	$(PYTEST) $(TESTS_DIR) --no-header -W ignore::DeprecationWarning

check: format lint test ## Run all checks (format, lint, test)

build: clean ## Build package distributions
	$(UV) build

install: build ## Install package locally
	$(UV) pip install .

publish: build ## Publish to PyPI
	$(UV) publish

dev: venv ## Start development server with auto-reload
	$(VENV_PYTHON) -m $(PACKAGE_NAME)

# Utility targets for development workflow
x: ## Copy project tree structure to clipboard (ignoring git files)
	@echo "==> Copying tree structure to clipboard"
	@tree --gitignore | $(COPY_TO_CLIPBOARD)

y: ## Run all checks and copy output to clipboard while displaying
	@echo "==> Running all checks and copying output..."
	@{ make check 2>&1; } | $(COPY_TO_CLIPBOARD)

z: ## Copy recent git log messages to clipboard while displaying
	@echo "==> Copying 8 most recent git log messages..."
	@{ git log -n8 2>&1; } | $(COPY_TO_CLIPBOARD)

r: ## Combine tree, make all, git log, and codestate outputs with separators
	@echo "==> Running combined commands and copying output..."
	@{ \
		echo -e "\n=== Git Log ==="; \
		git log -n8; \
		echo "=== Tree Structure ==="; \
		tree --gitignore; \
		echo -e "\n=== Check Output ==="; \
		make check; \
	} 2>&1 | $(COPY_TO_CLIPBOARD)

error: ## Run an erroneous command for test purposes.
	error
