# AWSUP Development Makefile

.PHONY: help install test lint clean build publish bump-patch bump-minor bump-major

help: ## Show this help message
	@echo "🚀 AWSUP Development Commands"
	@echo "=============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package in development mode
	pip install -e ".[dev]"

test: ## Run tests
	python -m pytest tests/test_validators.py tests/test_config.py -v

test-all: ## Run all tests (including integration)
	python -m pytest tests/ -v

lint: ## Run linting and formatting
	black src/ tests/ --check
	flake8 src/ tests/
	mypy src/

format: ## Format code
	black src/ tests/
	isort src/ tests/

security: ## Run security checks
	bandit -r src/

clean: ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info/ src/*.egg-info/ .pytest_cache/ .coverage htmlcov/

build: clean ## Build package
	python -m build

test-install: build ## Test package installation
	pip install dist/awsup-*.whl --force-reinstall
	awsup --help

bump-patch: ## Bump patch version (bug fixes)
	python scripts/bump_version.py patch

bump-minor: ## Bump minor version (new features)
	python scripts/bump_version.py minor

bump-major: ## Bump major version (breaking changes)
	python scripts/bump_version.py major

release: ## Create a release (interactive)
	@echo "🚀 Creating a new release..."
	@echo "Current version: $$(grep 'version =' pyproject.toml | cut -d'"' -f2)"
	@echo ""
	@echo "Choose bump type:"
	@echo "1) patch (bug fixes)"
	@echo "2) minor (new features)" 
	@echo "3) major (breaking changes)"
	@read -p "Enter choice (1-3): " choice; \
	case $$choice in \
		1) make bump-patch ;; \
		2) make bump-minor ;; \
		3) make bump-major ;; \
		*) echo "Invalid choice" && exit 1 ;; \
	esac
	@echo ""
	@NEW_VERSION=$$(grep 'version =' pyproject.toml | cut -d'"' -f2); \
	echo "📋 Next steps to publish v$$NEW_VERSION:"; \
	echo "1. git add -A"; \
	echo "2. git commit -m 'Bump version to $$NEW_VERSION'"; \
	echo "3. git tag v$$NEW_VERSION"; \
	echo "4. git push origin main --tags"

publish-test: build ## Publish to TestPyPI
	twine upload --repository testpypi dist/*

check-pypi: ## Check if package name is available on PyPI
	@python -c "import requests; resp = requests.get('https://pypi.org/pypi/awsup/json'); print('❌ Name taken' if resp.status_code == 200 else '✅ Name available')" 2>/dev/null || echo "✅ Name available"

dev-setup: ## Complete development setup
	pip install -e ".[dev]"
	pre-commit install || echo "pre-commit not available"

# Default target
.DEFAULT_GOAL := help