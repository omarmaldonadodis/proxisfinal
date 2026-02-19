# Makefile - DOCKER OPTIMIZADO (FINAL)
.PHONY: help docker-up docker-down docker-logs docker-restart docker-rebuild

# ========================================
# HELP
# ========================================
help:
	@echo "🐳 AdsPower Orchestrator - Docker Commands"
	@echo "=========================================="
	@echo ""
	@echo "📦 Docker Management:"
	@echo "  make docker-up           - Inicia containers"
	@echo "  make docker-down         - Detiene containers"
	@echo "  make docker-restart      - Reinicia containers"
	@echo "  make docker-rebuild      - Rebuild + restart"
	@echo "  make docker-logs         - Ver logs (API)"
	@echo "  make docker-logs-celery  - Ver logs (Celery Worker)"
	@echo "  make docker-logs-beat    - Ver logs (Celery Beat)"
	@echo ""
	@echo "🏥 Health Checks:"
	@echo "  make health-computers    - Check computers"
	@echo "  make health-proxies      - Check proxies"
	@echo ""
	@echo "💾 Backup:"
	@echo "  make backup-create       - Crear backup"
	@echo "  make backup-list         - Listar backups"
	@echo "  make backup-restore FILE=archivo.sql"
	@echo ""
	@echo "🗄️ Database:"
	@echo "  make db-migrate          - Ejecutar migraciones"
	@echo "  make db-shell            - PostgreSQL shell"
	@echo "  make db-backup-now       - Backup inmediato"
	@echo ""
	@echo "🧪 Development:"
	@echo "  make dev-shell           - Shell en API"
	@echo "  make dev-test            - Ejecutar tests"
	@echo "  make dev-lint            - Lint"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean-logs"
	@echo "  make clean-backups-old"
	@echo "  make clean-docker"

# ========================================
# DOCKER MANAGEMENT
# ========================================
docker-up:
	@echo "🚀 Starting Docker containers..."
	cd docker && docker compose up -d
	@echo "✅ Containers started!"
	@echo "📍 API:  http://localhost:8000"
	@echo "📍 Docs: http://localhost:8000/docs"

docker-down:
	@echo "🛑 Stopping Docker containers..."
	cd docker && docker compose down
	@echo "✅ Containers stopped!"

docker-restart:
	@echo "♻️ Restarting containers..."
	cd docker && docker compose restart
	@echo "✅ Containers restarted!"

docker-rebuild:
	@echo "🔨 Rebuilding containers..."
	cd docker && docker compose down && docker compose up -d --build
	@echo "✅ Containers rebuilt!"

docker-logs:
	docker logs -f adspower_api

docker-logs-celery:
	docker logs -f adspower_celery_worker

docker-logs-beat:
	docker logs -f adspower_celery_beat

docker-status:
	docker compose -f docker/docker-compose.yml ps


# ========================================
# HEALTH CHECKS
# ========================================
health-computers:
	bash scripts/cli_docker.sh health:computers

health-proxies:
	bash scripts/cli_docker.sh health:proxies --limit 50

# ========================================
# BACKUP
# ========================================
backup-create:
	@echo "💾 Creating backup..."
	docker exec adspower_api sh -c "cd /app && python -m cli.backup create"

backup-list:
	@echo "📂 Listing backups..."
	docker exec adspower_api sh -c "cd /app && python -m cli.backup list"

backup-restore:
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Usage: make backup-restore FILE=backup_YYYYMMDD_HHMMSS.sql"; \
		exit 1; \
	fi
	@echo "⚠️  WARNING: This will overwrite current database!"
	@read -p "Continue? (yes/no) " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker exec adspower_api sh -c "cd /app && python -m cli.backup restore $(FILE)"; \
	else \
		echo "Cancelled"; \
	fi

# ========================================
# DATABASE
# ========================================
db-migrate:
	@echo "🔄 Running migrations..."
	docker exec adspower_api sh -c "cd /app && alembic upgrade head"

db-shell:
	@echo "🐘 Opening PostgreSQL shell..."
	docker exec -it adspower_postgres psql -U adspower -d adspower_db

db-backup-now:
	@echo "📦 Triggering immediate backup..."
	docker exec adspower_api sh -c "cd /app && python -c 'from app.tasks.backup_tasks import backup_database_task; backup_database_task()'"

# ========================================
# DEVELOPMENT
# ========================================
dev-shell:
	docker exec -it adspower_api /bin/bash

dev-test:
	docker exec adspower_api sh -c "cd /app && pytest -v"

dev-lint:
	docker exec adspower_api sh -c "cd /app && flake8 app/"

# ========================================
# MONITORING
# ========================================
monitor-containers:
	watch -n 2 'docker stats --no-stream'

monitor-logs-all:
	docker compose -f docker/docker-compose.yml logs -f

# ========================================
# CLEANUP
# ========================================
clean-logs:
	@echo "🧹 Cleaning logs..."
	rm -f logs/*.log || true
	docker exec adspower_api sh -c "rm -f /app/logs/*.log || true"

clean-backups-old:
	@echo "🧹 Cleaning old backups (keeping last 7)..."
	docker exec adspower_api sh -c "cd /app && python -c 'from app.tasks.backup_tasks import cleanup_old_backups; cleanup_old_backups(\"/app/backups\", keep=7)'"

clean-docker:
	@echo "🧹 Cleaning Docker resources..."
	docker system prune -f
