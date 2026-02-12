.PHONY: help start stop logs status clean build index test commit

help:
	@echo "GLM RAG Pipeline - Available Commands:"
	@echo ""
	@echo "  make start        - Start RAG pipeline"
	@echo "  make stop         - Stop RAG pipeline"
	@echo "  make logs         - View logs"
	@echo "  make status       - Show container status"
	@echo "  make build        - Build RAG container"
	@echo "  make index        - Index PDFs in papers/"
	@echo "  make test         - Test RAG query"
	@echo "  make clean        - Remove containers and volumes"
	@echo "  make commit       - Git commit with timestamp"
	@echo ""
	@echo "Note: Pull GLM-4 model via Docker Desktop (Models tab)"

start:
	@echo "Starting RAG Pipeline..."
	@echo ""
	@echo "⚠️  Make sure glm-4-7-flash is pulled in Docker Desktop!"
	@echo ""
	docker compose up -d
	@echo ""
	@echo "✓ RAG Pipeline started!"
	@echo "  API: http://localhost:8000"
	@echo "  Docs: http://localhost:8000/docs"

stop:
	@echo "Stopping RAG pipeline..."
	docker compose down

logs:
	docker compose logs -f

status:
	@echo "=== Container Status ==="
	@docker compose ps
	@echo ""
	@echo "=== Git Status ==="
	@git status -s

build:
	@echo "Building RAG pipeline container..."
	docker compose build --no-cache

index:
	@echo "Indexing papers in papers/ directory..."
	docker compose exec rag-pipeline python -c "from app.rag import index_papers; index_papers()"
	@echo "✓ Papers indexed!"

test:
	@echo "Testing RAG query..."
	@curl -X POST http://localhost:8000/query \
		-H "Content-Type: application/json" \
		-d '{"question": "What are the main findings?", "top_k": 3}' \
		2>/dev/null | python3 -m json.tool

clean:
	@echo "⚠️  This will remove containers and volumes!"
	@read -p "Are you sure? [y/N]: " confirm; \
	if [ "$$confirm" = "y" ]; then \
		docker compose down -v; \
		echo "✓ Cleaned!"; \
	else \
		echo "Cancelled."; \
	fi

commit:
	@read -p "Commit message: " msg; \
	git add .; \
	git commit -m "$$msg [$$(date +'%Y-%m-%d %H:%M')]"
