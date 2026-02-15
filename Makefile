.PHONY: help start stop logs status clean rebuild index test

help:
	@echo "ArXivMind - Available Commands:"
	@echo ""
	@echo "  make start     - Start everything (Ollama + backend + frontend)"
	@echo "  make stop      - Stop all containers"
	@echo "  make logs      - Follow container logs"
	@echo "  make status    - Show service states"
	@echo "  make rebuild   - Stop, rebuild (no cache), start"
	@echo "  make clean     - Remove containers and volumes"
	@echo "  make index     - Trigger paper indexing"
	@echo "  make test      - Test RAG query"

start:
	@bash scripts/start.sh

stop:
	@echo "Stopping ArXivMind..."
	docker compose down

logs:
	docker compose logs -f

status:
	@echo "=== Container Status ==="
	@docker compose ps
	@echo ""
	@echo "=== Ollama Model ==="
	@ollama list 2>/dev/null | grep -E "glm4|NAME" || echo "Ollama not running or model not found"
	@echo ""
	@echo "=== Backend Health ==="
	@curl -sf http://localhost:8000/health 2>/dev/null | python3 -m json.tool || echo "Backend not responding"

rebuild:
	@echo "Rebuilding ArXivMind..."
	docker compose down
	docker compose build --no-cache
	@bash scripts/start.sh

clean:
	@echo "⚠️  This will remove containers and volumes!"
	@read -p "Are you sure? [y/N]: " confirm; \
	if [ "$$confirm" = "y" ]; then \
		docker compose down -v; \
		echo "✓ Cleaned!"; \
	else \
		echo "Cancelled."; \
	fi

index:
	@echo "Triggering paper indexing..."
	@curl -sf -X POST http://localhost:8000/index | python3 -m json.tool

test:
	@echo "Testing RAG query..."
	@curl -sf -X POST http://localhost:8000/query \
		-H "Content-Type: application/json" \
		-d '{"question": "What are the main findings?", "n_results": 3}' \
		| python3 -m json.tool
