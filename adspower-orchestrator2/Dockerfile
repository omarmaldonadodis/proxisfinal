# Dockerfile para el Orquestador - Solo Backend API
FROM python:3.11-slim

# Evitar buffering de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY docker/entrypoint.sh /entrypoint.sh

# Crear directorios necesarios
RUN mkdir -p logs static

# Dar permisos de ejecución al entrypoint
RUN chmod +x /entrypoint.sh

# Puerto expuesto
EXPOSE 8000

# Usar entrypoint que corre migraciones
ENTRYPOINT ["/entrypoint.sh"]
