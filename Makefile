# Makefile for common development tasks

.PHONY: help setup test test-unit test-integration docker-build docker-up docker-down lint format clean

help:
	@echo "Air Quality Platform - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup              Install all dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test               Run all tests"
	@echo "  make test-unit          Run unit tests only"
	@echo "  make test-integration   Run integration tests (requires Docker)"
	@echo "  make test-coverage      Run tests with coverage report"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build       Build all Docker images"
	@echo "  make docker-up          Start all services"
	@echo "  make docker-down        Stop all services"
	@echo "  make docker-logs        View Docker logs"
	@echo "  make docker-shell       Open shell in test container"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint               Run linting (flake8, pylint)"
	@echo "  make format             Format code (black)"
	@echo "  make type-check         Run type checking (mypy)"
	@echo ""
	@echo "Development:"
	@echo "  make clean              Remove build artifacts"
	@echo "  make venv               Create Python virtual environment"
	@echo "  make requirements        Install requirements"
	@echo "  make terraform-init     Initialize Terraform (dev)"
	@echo "  make terraform-plan     Plan Terraform deployment"

# Setup and dependencies
setup: venv requirements
	venv/bin/pip install -r requirements.txt

requirements:
	venv/bin/pip install -r requirements.txt

venv:
	python -m venv venv
	@echo "Virtual environment created. Activate with: source venv/bin/activate"

# Testing
test: test-unit test-integration

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit -v --tb=short

test-integration:
	@echo "Running integration tests with Docker..."
	docker-compose --profile test up --abort-on-container-exit

test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=lambdas --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:
	@echo "Running tests in watch mode..."
	pytest-watch tests/unit

# Docker commands
docker-build:
	@echo "Building Docker images..."
	docker-compose build

docker-up:
	@echo "Starting Docker services..."
	docker-compose up -d
	@echo "Services started. LocalStack available at http://localhost:4566"
	docker-compose ps

docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-logs-lambda:
	docker logs -f air-quality-lambda-test

docker-logs-tests:
	docker logs -f air-quality-tests

docker-shell:
	@echo "Opening shell in test container..."
	docker-compose exec integration-tests /bin/bash

docker-clean:
	docker-compose down -v
	docker system prune -a

# Code quality
lint:
	@echo "Running flake8..."
	flake8 lambdas tests --max-line-length=100 --ignore=E203,W503
	@echo "Running pylint..."
	pylint lambdas tests --exit-zero

format:
	@echo "Formatting code with black..."
	black lambdas tests --line-length=100
	@echo "Formatting complete"

type-check:
	@echo "Running type checking..."
	mypy lambdas --ignore-missing-imports

format-check:
	@echo "Checking code format..."
	black --check lambdas tests

# Terraform
terraform-init:
	cd terraform/environments/dev && terraform init

terraform-plan:
	cd terraform/environments/dev && terraform plan -var-file=terraform.dev.tfvars

terraform-apply:
	cd terraform/environments/dev && terraform apply -var-file=terraform.dev.tfvars

terraform-destroy:
	cd terraform/environments/dev && terraform destroy -var-file=terraform.dev.tfvars

# Cleanup
clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name *.pyc -delete
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .coverage -exec rm -rf {} +
	rm -rf .mypy_cache htmlcov dist build *.egg-info
	@echo "Cleanup complete"

clean-all: clean docker-clean
	@echo "Full cleanup complete"

# Development workflow
dev-setup: setup docker-build
	@echo "Development environment ready!"
	@echo "Next: make docker-up"

dev-start: docker-up
	@sleep 5
	@echo "Services started. Running tests..."
	@make test-unit

dev-test-all: docker-build docker-up
	@echo "Testing locally with Docker..."
	@docker-compose --profile test run integration-tests

dev-stop: docker-down

# Local Lambda testing
lambda-test: docker-up
	@echo "Starting Lambda runtime at http://localhost:9001"
	@docker-compose --profile lambda up lambda-test

lambda-invoke:
	@echo "Invoking Lambda function..."
	curl -X POST http://localhost:9001/2015-03-31/functions/function/invocations \
		-H "Content-Type: application/json" \
		-d '{}'

# Dashboard
dashboard-dev:
	@echo "Starting dashboard at http://localhost:3000"
	docker-compose --profile dashboard up dashboard

# LocalStack AWS CLI
localstack-config:
	aws configure --profile localstack
	localstack-s3-list:
	aws s3 ls --endpoint-url http://localhost:4566 --profile localstack

# Utilities
version:
	@echo "Project Version: 2.0.0"
	@echo "Python: $$(python --version)"
	@echo "Terraform: $$(terraform -version | head -1)"
	@echo "Docker: $$(docker --version)"

check-tools:
	@command -v python >/dev/null 2>&1 || { echo "Python not installed"; exit 1; }
	@command -v terraform >/dev/null 2>&1 || { echo "Terraform not installed"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "Docker not installed"; exit 1; }
	@echo "All required tools installed!"
