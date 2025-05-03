.PHONY: deploy destroy synth bootstrap clean venv install test help format lint type-check dev pre-commit-setup

# Python virtual environment
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

# Default target
all: venv install dev deploy

# Create and activate virtual environment
venv:
	python3 -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip

# Install dependencies
install: venv
	$(PIP) install -r requirements.txt
	$(PYTHON) -m pre_commit install

# Setup pre-commit hooks
pre-commit-setup: install
	$(PYTHON) -m pre_commit install --install-hooks

# Format code
format: install
	$(PYTHON) -m black .

# Lint code
lint: install
	$(PYTHON) -m flake8 .

# Type check
type-check: install
	$(PYTHON) -m mypy .

# Run all development checks
dev: format lint type-check test

# Deploy the stack
deploy: install
	$(PYTHON) -m cdk deploy --require-approval never

# Destroy the stack
destroy: install
	$(PYTHON) -m cdk destroy --force

# Synthesize CloudFormation template
synth: install
	$(PYTHON) -m cdk synth

# Bootstrap CDK in the current account/region
bootstrap: install
	$(PYTHON) -m cdk bootstrap

# Clean up build artifacts
clean:
	rm -rf cdk.out/
	rm -rf .cdk.staging/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".eggs" -exec rm -rf {} +
	find . -type d -name ".tox" -exec rm -rf {} +
	find . -type d -name ".nox" -exec rm -rf {} +
	find . -type d -name ".hypothesis" -exec rm -rf {} +
	rm -rf $(VENV_DIR)

# Run tests
test: install
	$(PYTHON) -m pytest tests/

# Help target
help:
	@echo "Available targets:"
	@echo "  venv            - Create Python virtual environment"
	@echo "  install         - Install dependencies"
	@echo "  pre-commit-setup - Setup pre-commit hooks"
	@echo "  format          - Format code with black"
	@echo "  lint            - Lint code with flake8"
	@echo "  type-check      - Type check with mypy"
	@echo "  dev             - Run all development checks"
	@echo "  deploy          - Deploy the stack"
	@echo "  destroy         - Destroy the stack"
	@echo "  synth           - Synthesize CloudFormation template"
	@echo "  bootstrap       - Bootstrap CDK in the current account/region"
	@echo "  clean           - Clean up build artifacts"
	@echo "  test            - Run tests" 