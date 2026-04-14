# WB Orchestrator — Guía de Inicialización

---

## 1. BACKEND — Configuración inicial

### 1.1 Archivo `.env` (crear en la raíz del proyecto)

```env
# ── App ──────────────────────────────────────────────
SECRET_KEY=genera_uno_con_openssl_rand_hex_32
DEBUG=False

# ── Base de datos ─────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://adspower:password@postgres:5432/adspower_db
DATABASE_SYNC_URL=postgresql+psycopg2://adspower:password@postgres:5432/adspower_db

# ── Redis ─────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── AdsPower (cuenta central) ─────────────────────────
ADSPOWER_DEFAULT_API_URL=http://local.adspower.net:50325
ADSPOWER_DEFAULT_API_KEY=TU_API_KEY_ADSPOWER

# ── SOAX ──────────────────────────────────────────────
SOAX_USERNAME=package-XXXXXX
SOAX_PASSWORD=TU_PASSWORD_SOAX
SOAX_HOST=proxy.soax.com
SOAX_PORT=5000
SOAX_API_KEY=TU_API_KEY_SOAX

# ── Seguridad agentes ─────────────────────────────────
AGENT_SECRET_TOKEN=genera_uno_con_openssl_rand_urlsafe_32

# ── Backups ───────────────────────────────────────────
BACKUP_ENABLED=True
BACKUP_INTERVAL=86400
BACKUP_PATH=/app/backups
```

### 1.2 Dónde obtener cada dato

| Variable | Dónde obtenerla |
|---|---|
| `SECRET_KEY` | Terminal: `openssl rand -hex 32` |
| `ADSPOWER_DEFAULT_API_KEY` | AdsPower → ⚙️ Settings → API → **Local API Key** |
| `SOAX_USERNAME` | Panel SOAX → Dashboard → tu paquete (formato `package-XXXXXX`) |
| `SOAX_PASSWORD` | Panel SOAX → Dashboard → contraseña del paquete |
| `SOAX_API_KEY` | Panel SOAX → API Keys |
| `AGENT_SECRET_TOKEN` | Terminal: `openssl rand -urlsafe 32` (mismo valor para todos los agentes) |

### 1.3 Levantar con Docker Compose

```bash
# Primera vez
docker compose -f docker/docker-compose.yml up -d --build

# Verificar que todo está OK
docker compose -f docker/docker-compose.yml logs -f api

# La API queda en: http://localhost:8000
# Docs: http://localhost:8000/docs
```

> Las migraciones/tablas se crean automáticamente al iniciar (`init_db()` en lifespan).

---

## 2. AGENTE — Configuración inicial

### 2.1 Primer arranque (interactivo)

Si el agente no tiene `config.json`, abre el asistente de configuración automáticamente.
Ejecutar desde la carpeta `agente/`:

```bash
python -m agent.main
```

Pide estos datos:

| Campo | Qué poner | Dónde obtenerlo |
|---|---|---|
| **URL del servidor** | `http://IP_SERVIDOR:8000` | IP de la máquina donde corre Docker |
| **Token de agente** | Token generado desde el panel admin | Panel → Admin → Agents → "Crear agente" → copiar token |
| **Tu nombre** | Nombre identificador del equipo/PC | Libre (ej. `Mac-Santiago`, `PC-Oficina-1`) |
| **URL de AdsPower local** | `http://local.adspower.net:50325` | Default — no cambiar salvo configuración custom |
| **API Key de AdsPower** | La key de AdsPower local | AdsPower → ⚙️ → API → **Local API Key** |

> El `config.json` se guarda en:
> - **Mac:** `~/Library/Application Support/AdsPowerAgent/config.json`
> - **Windows:** `%LOCALAPPDATA%\AdsPowerAgent\config.json`

Para testing si se reinicia la base de datos se debe borrar el contenido de esta carpeta

### 2.2 Crear el token del agente en el panel

El token se crea automáticamente al iniciar el proyecto por primera vez


---

## 3. BUILD DEL AGENTE — Pasos para producción

### 3.1 Qué se rellena en los distintos campos



```json
{
  "server_url": "https://tu-dominio-o-ip-produccion.com",
  "server_token": "AGENT_SECRET_TOKEN del .env",
  "adspower_url": "http://local.adspower.net:50325" (Verificar si esta ruta da en la computadora donde se instala soax),
  "computer_token": null,
  "adspower_url": 
}
```

Cambia `server_url` a la URL real de producción. El token y nombre los completa el usuario la primera vez.



### 3.2 Instalar dependencias de build

```bash
cd agente
pip install -r agent/requirements.txt
pip install pyinstaller
```

**Mac — dependencias extra:**
```bash
pip install rumps  # tray icon nativo macOS
```

**Windows:**
```bash
pip install pywin32
```

### 3.3 Comando de build

Desde la carpeta `agente/`:

```bash
# Mac
pyinstaller \
  --onefile \
  --windowed \
  --name "AdsPowerAgent" \
  --add-data "agent/build/config.json.template:." \
  --hidden-import "pystray._darwin" \
  --collect-all pystray \
  agent/main.py

# Windows (ejecutar en CMD)
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "AdsPowerAgent" ^
  --add-data "agent\build\config.json.template;." ^
  --hidden-import "pystray._win32" ^
  --collect-all pystray ^
  agent\main.py
```

El ejecutable final queda en `agente/dist/AdsPowerAgent` (Mac) o `agente/dist/AdsPowerAgent.exe` (Windows).

### 3.4 Checklist antes de distribuir el build

- [ ] `server_url` en `config.json.template` apunta a producción
- [ ] `AGENT_SECRET_TOKEN` en el `.env` del servidor y en los tokens generados es el mismo
- [ ] `ADSPOWER_DEFAULT_API_URL` en `.env` apunta a la instancia de AdsPower correcta
- [ ] El puerto `8000` del servidor es accesible desde las máquinas de los agentes
- [ ] AdsPower está instalado y abierto en la máquina antes de ejecutar el agente



## 4. Flujo completo de primera puesta en marcha

```
1. Copiar y rellenar .env
2. docker compose up -d --build
3. Abrir http://localhost:8000/docs
4. En cada PC: abrir AdsPower, ejecutar AdsPowerAgent
5. El agente pide los datos → ingresar URL del servidor + token creado en paso 4
6. Verificar en el panel que el agente aparece ONLINE
```
