# AquaNet Puebla 

Plataforma web de gestión hídrica inteligente para el municipio de Puebla.
Centraliza reportes ciudadanos, prioriza incidencias y simula el impacto de fallas en la red de distribución.

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 + Flask 3.0 |
| Base de datos | PostgreSQL 16 + PostGIS |
| Algoritmos de red | NetworkX 3.x |
| Tareas programadas | APScheduler |
| Mapas | Leaflet.js + OpenStreetMap |
| Gráficas | Chart.js |
| UI | Bootstrap 5 |

---

## Estructura del proyecto

```
aquanet/
├── app/
│   ├── __init__.py          ← Factory de Flask
│   ├── database.py          ← Conexión PostgreSQL
│   ├── auth/                ← Autenticación y roles (Fase 2)
│   │   ├── models.py
│   │   ├── decorators.py
│   │   └── routes.py
│   ├── reportes/            ← Módulo de reportes (Fase 3)
│   ├── mapa/                ← Mapa inteligente (Fase 4)
│   ├── prioridad/           ← Motor IP (Fase 4)
│   ├── simulador/           ← Simulador de red (Fase 5)
│   ├── dashboard/           ← Dashboard analítico (Fase 6)
│   ├── admin/               ← Panel de administrador (Fase 6)
│   ├── static/
│   └── templates/
├── config/
│   └── settings.py          ← Configuración por entorno
├── database/
│   └── migrations/          ← Migraciones versionadas con Flyway
│       ├── V1__init_schema.sql
│       ├── V2__seed_usuarios.sql
│       └── V3__seed_demo_datos.sql
├── scripts/
│   ├── init_db.py           ← Inicializar BD / Migraciones desde Python
│   └── crear_usuario.py     ← Sembrador de usuarios de demostración
├── tests/                   ← Suite de pruebas unitarias (13 tests)
├── docker-compose.yml       ← PostgreSQL 17 + PostGIS + Flyway
├── .env.example
├── .gitignore
├── .dockerignore
├── requirements.txt
└── run.py                   ← Punto de entrada
```

---

## Puesta en marcha rápida (Docker + Flyway)

La forma recomendada de ejecutar la base de datos es mediante Docker, aislando PostgreSQL 17 con PostGIS y aplicando las migraciones automáticamente con Flyway.

### 1. Iniciar Base de Datos y Migraciones con Docker

```bash
# Inicia PostgreSQL 17 (PostGIS 3.5) y aplica migraciones de Flyway
docker compose up -d
```

### 2. Configurar entorno virtual e instalar dependencias

```bash
python -m venv venv
venv\Scripts\activate          # En Windows
# source venv/bin/activate     # En Linux/Mac
pip install -r requirements.txt
```

### 3. Iniciar la aplicación web

```bash
python run.py
# o
flask run --debug
```

Abre http://localhost:5000

---

## Usuarios de demostración (Listos para presentación y pruebas)

El sistema incluye 3 cuentas preconfiguradas y sembradas automáticamente por Flyway (`V2__seed_usuarios.sql`):

| Rol | Correo electrónico | Contraseña | Permisos y Alcance |
|-----|-------------------|------------|--------------------|
| **Administrador** | `admin@aquanet.mx` | `Admin1234` | Panel general, KPIs, gestión de usuarios, edición de nodos y tuberías del grafo hídrico. |
| **Operador** | `operador@aquanet.mx` | `Operador1234` | Gestión de reportes ciudadanos, cambio de estados, asignación y acceso al **Simulador de Red Hídrica**. |
| **Ciudadano** | `ciudadano@aquanet.mx` | `Ciudadano1234` | Consulta de reportes, creación de incidencias georreferenciadas con fotos y seguimiento. |

---

## Conexión desde DBeaver

Puedes inspeccionar y gestionar la base de datos visualmente conectando DBeaver al contenedor:

* **Gestor:** PostgreSQL
* **Host:** `localhost`
* **Port:** `5435` *(mapeado para evitar colisiones locales)*
* **Database:** `aquanet_puebla`
* **Username:** `postgres`
* **Password:** `12345`

> **Visualización espacial:** En DBeaver, al hacer `SELECT geom FROM reportes` o `nodos_red`, activa la pestaña **"Spatial"** para ver los puntos proyectados directamente sobre el mapa de OpenStreetMap.

---

## Migraciones con Flyway

Las migraciones SQL se versionan en `database/migrations/`:
- `V1__init_schema.sql`: Extensiones PostGIS, enums, 14 tablas, triggers espaciales y vistas.
- `V2__seed_usuarios.sql`: Usuarios iniciales de prueba (Admin, Operador, Ciudadano) con hashes seguros en `bcrypt`.
- `V3__seed_demo_datos.sql`: Zonas de Puebla, nodos y tuberías de la red hídrica, y reportes iniciales.

Para aplicar migraciones sin Docker manualmente:
```bash
python scripts/init_db.py
```

---

## Motor de priorización

**IP = (G × 0.35) + (D × 0.25) + (T × 0.25) + (R × 0.15)**

| Variable | Descripción | Peso |
|----------|-------------|------|
| G | Gravedad del tipo de incidencia | 35% |
| D | Densidad poblacional de la zona | 25% |
| T | Tiempo sin atención (logarítmico) | 25% |
| R | Recurrencia histórica 90 días | 15% |

| Nivel | Rango IP | SLA |
|-------|----------|-----|
| Crítica | 80-100 | 4 horas |
| Alta | 60-79 | 12 horas |
| Media | 40-59 | 48 horas |
| Baja | 0-39 | 7 días |

---

### 7. Ejecutar pruebas unitarias

```bash
# Con el entorno virtual activo:
python -m unittest discover tests
```

---

## Fases de desarrollo

- [x] **Fase 1** — Entorno, estructura Flask y base de datos PostgreSQL/PostGIS
- [x] **Fase 2** — Autenticación y roles (bcrypt + Flask-Login + bloqueo anti-fuerza bruta)
- [x] **Fase 3** — Módulo de reportes ciudadanos (CRUD, mapa, evidencia fotográfica, exportación CSV)
- [x] **Fase 4** — Motor IP (recálculo periódico con APScheduler) + mapa inteligente con Leaflet
- [x] **Fase 5** — Simulador de red hídrica con NetworkX (fallas de nodos y tuberías)
- [x] **Fase 6** — Dashboard analítico (KPIs, Chart.js) + panel de administración de usuarios y red
