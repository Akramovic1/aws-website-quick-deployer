# AWS Website Quick Deployer - Development Commands

.PHONY: help install test lint format security clean

help:		## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:	## Install all dependencies
	pip install -r requirements.txt

test:		## Run all tests
	python -m pytest tests/ -v

test-cov:	## Run tests with coverage
	python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-unit:	## Run only unit tests
	python -m pytest tests/ -v -m unit

test-security:	## Run security tests
	python -m pytest tests/ -v -m security
	bandit -r src/

lint:		## Run code linting
	flake8 src/ tests/
	mypy src/

format:		## Format code
	black src/ tests/
	isort src/ tests/

security:	## Run security scanning
	bandit -r src/
	safety check

validate:	## Validate syntax
	python -m py_compile aws_deploy.py
	python -m py_compile deploy_production.py

clean:		## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

# Development workflow
dev-setup:	## Setup development environment
	pip install -r requirements.txt
	pre-commit install

dev-test:	## Development testing (fast)
	python -m pytest tests/ -x --tb=short

# Production commands  
deploy-dev:	## Deploy to development environment
	python deploy_production.py init dev.$(DOMAIN) --environment dev
	python deploy_production.py phase1 dev.$(DOMAIN)
	python deploy_production.py phase2 dev.$(DOMAIN)

deploy-prod:	## Deploy to production environment  
	python deploy_production.py init $(DOMAIN) --environment prod
	python deploy_production.py phase1 $(DOMAIN)
	python deploy_production.py phase2 $(DOMAIN) --website-path ./dist