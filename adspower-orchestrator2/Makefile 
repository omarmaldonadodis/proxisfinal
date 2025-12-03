# Makefile
.PHONY: help install setup migrate test run clean docker-up docker-down

help:
	@echo "AdsPower Orchestrator - Comandos disponibles:"
	@echo ""
	@echo "  make install      - Instala dependencias"
	@echo "  make setup        - Setup completo (DB + migraciones)"
	@echo "  make migrate      - Ejecuta migraciones"
	@echo "  make test         - Ejecuta tests"
	@echo "  make run          - Inicia servidor de desarrollo"
	@echo "  make celery       - Inicia Celery worker"
	@echo "  make clean        - Limpia archivos temporales"
	@echo "  make docker-up    - Inicia con Docker"
	@echo "  make docker-down  - Detiene Docker"
	@echo ""

install:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

setup:
	bash scripts/setup_complete.sh

migrate:
	. venv/bin/activate && alembic upgrade head

test:
	. venv/bin/activate && pytest -v

run:
	. venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

celery:
	. venv/bin/activate && celery -A app.tasks worker --loglevel=info

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-up:
	cd docker && docker-compose up -d

docker-down:
	cd docker && docker-compose down

docker-logs:
	cd docker && docker-compose logs -f api

backup:
	. venv/bin/activate && python cli/backup.py create

health:
	. venv/bin/activate && python cli/health_check.py computers