.PHONY: help install dev test build up down logs clean format lint

# Default target
help:
	@echo "RDAgent - Available Commands:"
	@echo ""
	@echo "Local Development (with uv):"
	@echo "  make install       - Install dependencies with uv"
	@echo "  make install-all   - Install with all optional dependencies"
	@echo "  make dev           - Run development server"
	@echo "  make test          - Run tests"
	@echo "  make test-cov      - Run tests with coverage"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make build         - Build Docker images"
	@echo "  make up            - Start all services (docker-compose up -d)"
	@echo "  make down          - Stop all services"
	@echo "  make logs          - View logs"
	@echo "  make shell         - Open shell in development container"
	@echo ""
	@echo "Individual Services:"
	@echo "  make api           - Start API server only"
	@echo "  make ui            - Start Streamlit UI only"
	@echo "  make dev-shell     - Open development shell with volume mounts"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean         - Remove build artifacts and containers"
	@echo "  make clean-all     - Full cleanup including volumes"
	@echo "  make format        - Format code (if tools available)"
	@echo "  make lint          - Run linters (if tools available)"

# ==========================================
# Local Development with uv
# ==========================================
install:
	@echo "Installing dependencies with uv..."
	uv venv
	uv pip install -e "."

install-all:
	@echo "Installing all dependencies with uv..."
	uv venv
	uv pip install -e ".[all]"

dev:
	@echo "Starting development server..."
	python -m app.startup

test:
	@echo "Running tests..."
	pytest tests/ -v

test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ -v --cov=. --cov-report=term-missing

# ==========================================
# Docker Commands
# ==========================================
build:
	@echo "Building Docker images..."
	docker-compose build

up:
	@echo "Starting services..."
	docker-compose up -d

down:
	@echo "Stopping services..."
	docker-compose down

logs:
	@echo "Viewing logs..."
	docker-compose logs -f

shell:
	@echo "Opening shell in app container..."
	docker-compose exec app /bin/bash

# ==========================================
# Individual Services
# ==========================================
api:
	@echo "Starting API server..."
	docker-compose up -d api
	@echo "API available at http://localhost:8000"
	@echo "Health check: http://localhost:8000/health"

ui:
	@echo "Starting Streamlit UI..."
	docker-compose up -d ui
	@echo "UI available at http://localhost:8501"

dev-shell:
	@echo "Opening development shell..."
	docker-compose run --rm dev

# ==========================================
# Quick Start
# ==========================================
quickstart:
	@echo "Quick Start - Building and starting all services..."
	cp config.example.yaml config.yaml 2>/dev/null || true
	docker-compose up -d api ui
	@echo ""
	@echo "Services started:"
	@echo "  API: http://localhost:8000"
	@echo "  UI:  http://localhost:8501"
	@echo ""
	@echo "To run an experiment:"
	@echo "  docker-compose exec app python cli.py --scenario data_science --task 'classify iris dataset'"

# ==========================================
# Maintenance
# ==========================================
clean:
	@echo "Cleaning up..."
	docker-compose down --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

clean-all: clean
	@echo "Full cleanup including volumes..."
	docker-compose down -v
	docker system prune -f

format:
	@echo "Formatting code..."
	@if command -v black >/dev/null 2>&1; then \
		black .; \
	else \
		echo "black not installed, skipping"; \
	fi
	@if command -v isort >/dev/null 2>&1; then \
		isort .; \
	else \
		echo "isort not installed, skipping"; \
	fi

lint:
	@echo "Running linters..."
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check .; \
	else \
		echo "ruff not installed, skipping"; \
	fi
	@if command -v mypy >/dev/null 2>&1; then \
		mypy .; \
	else \
		echo "mypy not installed, skipping"; \
	fi

# ==========================================
# Configuration
# ==========================================
config:
	@if [ ! -f config.yaml ]; then \
		echo "Creating config.yaml from example..."; \
		cp config.example.yaml config.yaml; \
		echo "Please edit config.yaml with your settings"; \
	else \
		echo "config.yaml already exists"; \
	fi

# ==========================================
# Examples
# ==========================================
example-simple:
	@echo "Running simple example..."
	python cli.py --config config.yaml --scenario data_science --task "classify iris dataset" --max-steps 3

example-api:
	@echo "Running example via API..."
	curl -X POST http://localhost:8000/runs \
		-H "Content-Type: application/json" \
		-d '{"scenario": "data_science", "task_summary": "classify iris dataset", "max_loops": 3}'
