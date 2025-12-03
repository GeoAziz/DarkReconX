.PHONY: help install install-dev test lint fmt check-fmt clean clean-cache clean-pyc clean-test coverage pre-commit-install ci

help:
	@echo "DarkReconX Development Commands"
	@echo "================================"
	@echo "  make install          - Install project dependencies"
	@echo "  make install-dev      - Install with dev tools (pytest, black, flake8, etc.)"
	@echo "  make test             - Run unit tests"
	@echo "  make test-cov         - Run tests with coverage report"
	@echo "  make test-integration - Run integration tests (requires API keys)"
	@echo "  make lint             - Run flake8 linter"
	@echo "  make fmt              - Auto-format code with black and isort"
	@echo "  make check-fmt        - Check formatting without changes"
	@echo "  make type-check       - Run mypy type checker"
	@echo "  make pre-commit-install - Install pre-commit hooks"
	@echo "  make pre-commit-run   - Run pre-commit hooks on all files"
	@echo "  make ci               - Run full CI pipeline (lint + test)"
	@echo "  make clean            - Remove all build/test artifacts"
	@echo "  make clean-cache      - Remove .cache and .coverage files"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v -k "not integration"

test-cov:
	pytest tests/ -v --cov=core --cov=config --cov=modules --cov-report=html --cov-report=term-missing -k "not integration"

test-integration:
	RUN_API_INTEGRATION=1 pytest tests/ -v -k "integration" -m "integration"

lint:
	flake8 . --max-line-length=127 --exclude=.git,__pycache__,venv --statistics

fmt:
	black .
	isort .

check-fmt:
	black --check .
	isort --check-only .

type-check:
	mypy --ignore-missing-imports . || true

pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

ci: lint test
	@echo "✅ CI pipeline passed!"

clean: clean-build clean-pyc clean-test clean-cache
	@echo "✅ Cleaned all artifacts"

clean-build:
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/
	find . -name '*.egg-info' -exec rm -rf {} + || true

clean-pyc:
	find . -type f -name '*.py[cod]' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} + || true

clean-test:
	rm -rf .tox/
	rm -f .coverage
	rm -rf htmlcov/

clean-cache:
	rm -rf .cache/

update-deps:
	pip install --upgrade pip
	pip install --upgrade -e ".[dev]"
