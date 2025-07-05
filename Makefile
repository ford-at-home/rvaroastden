.PHONY: deploy destroy synth bootstrap clean venv install test help format lint type-check dev pre-commit-setup

# Python virtual environment
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

# Variables
AWS_REGION ?= us-east-1
AWS_ACCOUNT_ID ?= $(shell aws sts get-caller-identity --query Account --output text)
CDK_ENV := aws://$(AWS_ACCOUNT_ID)/$(AWS_REGION)
CDK_APP := "$(PYTHON) simulchaos_cdk_stack.py"

# Default target
all: venv install dev deploy

# Create and activate virtual environment
venv:
	@echo "Creating virtual environment..."
	python3 -m venv $(VENV_DIR)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

# Install dependencies
install:
	@echo "Installing dependencies..."
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pre_commit install

# Setup pre-commit hooks
pre-commit-setup:
	@echo "Setting up pre-commit hooks..."
	$(PYTHON) -m pre_commit install --install-hooks

# Format code
format:
	@echo "Formatting code..."
	$(PYTHON) -m black .
	$(PYTHON) -m isort .

# Lint code
lint:
	@echo "Linting code..."
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy .

# Type check
type-check:
	@echo "Type checking..."
	$(PYTHON) -m mypy .

# Run all development checks
dev: format lint type-check test

# Deploy the stack
deploy:
	@echo "Deploying CDK stack..."
	$(PYTHON) -m pip install -r requirements.txt
	cdk deploy --app $(CDK_APP) --require-approval never

# Destroy the stack
destroy:
	@echo "Destroying CDK stack..."
	$(PYTHON) -m pip install -r requirements.txt
	cdk destroy --app $(CDK_APP) --force

# Synthesize CloudFormation template
synth:
	@echo "Synthesizing CDK stack..."
	$(PYTHON) -m pip install -r requirements.txt
	cdk synth --app $(CDK_APP)

# Bootstrap CDK in the current account/region
bootstrap:
	@echo "Bootstrapping CDK environment..."
	$(PYTHON) -m pip install -r requirements.txt
	cdk bootstrap --app $(CDK_APP) $(CDK_ENV)

# Clean up build artifacts
clean:
	@echo "Cleaning up..."
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
test:
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/ -v

# Run tests with coverage
coverage:
	@echo "Running tests with coverage..."
	$(PYTHON) -m pytest tests/ --cov=. --cov-report=html

# Help target
help:
	@echo "Available commands:"
	@echo "  make venv              - Create virtual environment"
	@echo "  make install           - Install dependencies"
	@echo "  make clean             - Clean up generated files"
	@echo "  make test              - Run tests"
	@echo "  make coverage          - Run tests with coverage"
	@echo "  make format            - Format code"
	@echo "  make lint              - Lint code"
	@echo "  make type-check        - Type check code"
	@echo "  make dev               - Run all code quality checks"
	@echo "  make pre-commit-setup  - Set up pre-commit hooks"
	@echo "  make bootstrap         - Bootstrap CDK environment"
	@echo "  make deploy            - Deploy CDK stack"
	@echo "  make destroy           - Destroy CDK stack"
	@echo "  make synth             - Synthesize CDK stack"
	@echo ""
	@echo "Environment variables:"
	@echo "  AWS_REGION             - AWS region (default: us-east-1)"
	@echo "  AWS_ACCOUNT_ID         - AWS account ID (auto-detected)"
	@echo "  CDK_APP                - CDK app entry point (default: $(PYTHON) simulchaos_cdk_stack.py)" 