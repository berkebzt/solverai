.PHONY: help build up down logs restart clean install-model test

help:
	@echo "SolverAI - AI Companion Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs (all services)"
	@echo "  make logs-api       - View API logs only"
	@echo "  make logs-ollama    - View Ollama logs only"
	@echo "  make install-model  - Download Llama 3.1 8B model"
	@echo "  make shell-api      - Open shell in API container"
	@echo "  make shell-ollama   - Open shell in Ollama container"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Remove all containers and volumes"
	@echo "  make dev            - Start in development mode"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Waiting for services to start..."
	@sleep 5
	@echo "Services started! API available at http://localhost:8000"
	@echo "Run 'make install-model' to download Llama 3.1"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-ollama:
	docker-compose logs -f ollama

install-model:
	@echo "Downloading Llama 3.1 8B model (this may take a while)..."
	docker exec -it solverai-ollama ollama pull llama3.1:8b
	@echo "Model installed successfully!"

shell-api:
	docker exec -it solverai-api /bin/bash

shell-ollama:
	docker exec -it solverai-ollama /bin/bash

test:
	docker exec solverai-api pytest

clean:
	docker-compose down -v
	@echo "All containers and volumes removed"

dev:
	docker-compose up
