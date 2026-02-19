# Alembic Migrations

Este directorio contiene las migraciones de base de datos de Alembic.

## Comandos útiles

### Crear nueva migración
```bash
# Auto-generar migración desde modelos
alembic revision --autogenerate -m "descripción del cambio"

# Crear migración vacía
alembic revision -m "descripción del cambio"
```

### Aplicar migraciones
```bash
# Aplicar todas las migraciones pendientes
alembic upgrade head

# Aplicar una migración específica
alembic upgrade <revision_id>

# Aplicar siguiente migración
alembic upgrade +1
```

### Revertir migraciones
```bash
# Revertir última migración
alembic downgrade -1

# Revertir todas las migraciones
alembic downgrade base

# Revertir a revisión específica
alembic downgrade <revision_id>
```

### Ver estado
```bash
# Ver migración actual
alembic current

# Ver historial de migraciones
alembic history

# Ver migraciones pendientes
alembic show
```

## Estructura de archivos

- `env.py` - Configuración de Alembic
- `script.py.mako` - Template para nuevas migraciones
- `versions/` - Directorio con archivos de migración
  - `001_initial_migration.py` - Migración inicial con todas las tablas
```

---

## 📋 ESTRUCTURA FINAL COMPLETA
```
adspower-orchestrator/
├── .gitignore                          ✅ NUEVO
├── .env.example                        ✅ YA LO TIENES
├── Makefile                            ✅ NUEVO (OPCIONAL)
├── README.md                           ✅ YA LO TIENES
├── requirements.txt                    ✅ YA LO TIENES
├── pytest.ini                          ✅ YA LO TIENES
├── alembic.ini                         ✅ YA LO TIENES
│
├── alembic/
│   ├── __init__.py                     ✅ NUEVO
│   ├── README                          ✅ NUEVO
│   ├── env.py                          ✅ YA LO TIENES
│   ├── script.py.mako                  ✅ NUEVO
│   └── versions/
│       ├── .gitkeep                    ✅ NUEVO
│       └── 001_initial_migration.py    ✅ NUEVO
│
├── app/
│   ├── __init__.py                     ✅ NUEVO
│   ├── main.py                         ✅ YA LO TIENES
│   ├── config.py                       ✅ YA LO TIENES
│   ├── database.py                     ✅ YA LO TIENES
│   │
│   ├── models/
│   │   ├── __init__.py                 ✅ YA LO TIENES
│   │   ├── computer.py                 ✅ YA LO TIENES
│   │   ├── proxy.py                    ✅ YA LO TIENES
│   │   ├── profile.py                  ✅ YA LO TIENES
│   │   ├── task.py                     ✅ YA LO TIENES
│   │   └── health_check.py             ✅ YA LO TIENES
│   │
│   ├── schemas/
│   │   ├── __init__.py                 ✅ NUEVO
│   │   ├── computer.py                 ✅ YA LO TIENES
│   │   ├── proxy.py                    ✅ YA LO TIENES
│   │   ├── profile.py                  ✅ YA LO TIENES
│   │   ├── task.py                     ✅ NUEVO
│   │   └── automation.py               ✅ YA LO TIENES
│   │
│   ├── api/
│   │   ├── __init__.py                 ✅ NUEVO
│   │   └── v1/
│   │       ├── __init__.py             ✅ NUEVO
│   │       ├── computers.py            ✅ YA LO TIENES
│   │       ├── proxies.py              ✅ YA LO TIENES
│   │       ├── profiles.py             ✅ YA LO TIENES
│   │       ├── tasks.py                ✅ NUEVO
│   │       ├── health.py               ✅ NUEVO
│   │       └── automation.py           ✅ YA LO TIENES
│   │
│   ├── services/
│   │   ├── __init__.py                 ✅ NUEVO
│   │   ├── computer_service.py         ✅ YA LO TIENES
│   │   ├── proxy_service.py            ✅ YA LO TIENES
│   │   ├── profile_service.py          ✅ YA LO TIENES
│   │   ├── task_service.py             ✅ NUEVO
│   │   ├── health_service.py           ✅ NUEVO
│   │   └── automation_service.py       ✅ YA LO TIENES
│   │
│   ├── repositories/
│   │   ├── __init__.py                 ✅ NUEVO
│   │   ├── base.py                     ✅ YA LO TIENES
│   │   ├── computer_repository.py      ✅ YA LO TIENES
│   │   ├── proxy_repository.py         ✅ YA LO TIENES
│   │   ├── profile_repository.py       ✅ YA LO TIENES
│   │   └── task_repository.py          ✅ YA LO TIENES
│   │
│   ├── integrations/
│   │   ├── __init__.py                 ✅ NUEVO
│   │   ├── adspower_client.py          ✅ YA LO TIENES
│   │   ├── soax_client.py              ✅ YA LO TIENES
│   │   └── threexui_client.py          ✅ NUEVO
│   │
│   ├── core/
│   │   ├── __init__.py                 ✅ NUEVO
│   │   ├── exceptions.py               ✅ NUEVO
│   │   ├── security.py                 ✅ NUEVO
│   │   ├── logging.py                  ✅ NUEVO
│   │   └── dependencies.py             ✅ NUEVO
│   │
│   └── tasks/
│       ├── __init__.py                 ✅ YA LO TIENES
│       ├── profile_tasks.py            ✅ YA LO TIENES
│       ├── automation_tasks.py         ✅ YA LO TIENES
│       ├── health_tasks.py             ✅ YA LO TIENES
│       └── backup_tasks.py             ✅ YA LO TIENES
│
├── cli/
│   ├── __init__.py                     ✅ NUEVO
│   ├── create_profile.py               ✅ YA LO TIENES
│   ├── bulk_operations.py              ✅ YA LO TIENES
│   ├── health_check.py                 ✅ YA LO TIENES
│   └── backup.py                       ✅ NUEVO
│
├── tests/
│   ├── __init__.py                     ✅ NUEVO
│   ├── conftest.py                     ✅ NUEVO
│   ├── test_api/
│   │   ├── __init__.py                 ✅ NUEVO
│   │   ├── test_computers.py           ✅ NUEVO
│   │   └── test_health.py              ✅ NUEVO
│   ├── test_services/
│   │   ├── __init__.py                 ✅ NUEVO
│   │   └── test_computer_service.py    ✅ NUEVO
│   └── test_repositories/
│       ├── __init__.py                 ✅ NUEVO
│       └── test_computer_repository.py ✅ NUEVO
│
├── docker/
│   ├── Dockerfile                      ✅ YA LO TIENES
│   ├── docker-compose.yml              ✅ YA LO TIENES
│   └── nginx.conf                      ✅ NUEVO
│
├── scripts/
│   ├── init_project.sh                 ✅ NUEVO
│   ├── setup_complete.sh               ✅ NUEVO
│   ├── setup_db.sh                     ✅ YA LO TIENES
│   ├── run_migrations.sh               ✅ YA LO TIENES
│   ├── backup.sh                       ✅ NUEVO
│   └── start_dev.sh                    ✅ YA LO TIENES
│
├── logs/
│   └── .gitkeep                        ✅ NUEVO
│
├── backups/
│   └── .gitkeep                        ✅ NUEVO
│
└── profiles/
    ├── .gitkeep                        ✅ NUEVO
    ├── profile_data/
    │   └── .gitkeep                    ✅ NUEVO
    └── warmup_reports/
        └── .gitkeep                    ✅ NUEVO