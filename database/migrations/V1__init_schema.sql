-- ═══════════════════════════════════════════════════════════════
--  AquaNet Puebla — Schema completo de base de datos
--  PostgreSQL 16 + PostGIS
--  Ejecutar con: psql -U aquanet_user -d aquanet_puebla -f schema.sql
-- ═══════════════════════════════════════════════════════════════

-- Habilitar extensión PostGIS (ejecutar como superusuario la primera vez)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────────────────────
--  TIPOS ENUM
-- ─────────────────────────────────────────────────────────────

CREATE TYPE rol_usuario AS ENUM (
    'ciudadano',
    'operador',
    'administrador'
);

CREATE TYPE estado_reporte AS ENUM (
    'recibido',
    'en_revision',
    'asignado',
    'en_atencion',
    'resuelto',
    'cerrado'
);

CREATE TYPE tipo_nodo AS ENUM (
    'deposito',
    'distribucion',
    'colonia'
);

CREATE TYPE estado_arista AS ENUM (
    'activa',
    'falla',
    'mantenimiento'
);

CREATE TYPE tipo_notificacion AS ENUM (
    'cambio_estado',
    'asignacion',
    'sla_proximo',
    'sla_vencido',
    'sistema'
);

-- ─────────────────────────────────────────────────────────────
--  TABLA 1: usuarios
--  Ciudadanos, operadores y administradores del sistema
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
    id                  SERIAL PRIMARY KEY,
    nombre              VARCHAR(120)    NOT NULL,
    email               VARCHAR(180)    NOT NULL UNIQUE,
    password_hash       VARCHAR(255)    NOT NULL,
    telefono            VARCHAR(20),
    curp                VARCHAR(18),
    colonia             VARCHAR(120),
    rol                 rol_usuario     NOT NULL DEFAULT 'ciudadano',
    activo              BOOLEAN         NOT NULL DEFAULT TRUE,
    intentos_fallidos   INTEGER         NOT NULL DEFAULT 0,
    bloqueado_hasta     TIMESTAMPTZ,
    fecha_registro      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    ultimo_acceso       TIMESTAMPTZ
);

CREATE INDEX idx_usuarios_email ON usuarios(email);
CREATE INDEX idx_usuarios_rol   ON usuarios(rol);

-- ─────────────────────────────────────────────────────────────
--  TABLA 2: zonas
--  Colonias y sectores del municipio de Puebla
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zonas (
    id                      SERIAL PRIMARY KEY,
    nombre                  VARCHAR(120)    NOT NULL,
    municipio               VARCHAR(80)     NOT NULL DEFAULT 'Puebla',
    latitud                 DECIMAL(10,7)   NOT NULL,
    longitud                DECIMAL(10,7)   NOT NULL,
    geom                    GEOMETRY(POINT, 4326),  -- PostGIS
    poblacion               INTEGER         NOT NULL DEFAULT 0,
    nivel_riesgo_historico  DECIMAL(5,2)    NOT NULL DEFAULT 0.0,
    activa                  BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_zonas_geom ON zonas USING GIST(geom);

-- Trigger: sincronizar latitud/longitud → geom PostGIS
CREATE OR REPLACE FUNCTION sync_zona_geom()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitud, NEW.latitud), 4326);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_zona_geom
    BEFORE INSERT OR UPDATE OF latitud, longitud ON zonas
    FOR EACH ROW EXECUTE FUNCTION sync_zona_geom();

-- ─────────────────────────────────────────────────────────────
--  TABLA 3: tipos_incidencia
--  Catálogo de problemas con su peso de gravedad
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tipos_incidencia (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(80)     NOT NULL UNIQUE,
    peso_gravedad   DECIMAL(4,2)    NOT NULL CHECK (peso_gravedad BETWEEN 0 AND 10),
    descripcion     TEXT,
    activo          BOOLEAN         NOT NULL DEFAULT TRUE
);

-- Datos iniciales del catálogo
INSERT INTO tipos_incidencia (nombre, peso_gravedad, descripcion) VALUES
    ('Fuga en tubería maestra',  10.0, 'Fuga visible de gran volumen en tubería principal'),
    ('Fuga en tubería menor',     7.0, 'Fuga de bajo caudal en tubería secundaria'),
    ('Corte total de suministro', 9.0, 'Sin agua en la zona por falla o mantenimiento'),
    ('Baja presión severa',       6.5, 'Presión notoriamente insuficiente para uso doméstico'),
    ('Baja presión leve',         3.0, 'Reducción leve de presión, uso posible con dificultad'),
    ('Agua contaminada',          8.5, 'Cambio de color, olor o turbidez en el agua'),
    ('Drenaje obstruido',         5.0, 'Tapón o desbordamiento en la red de drenaje'),
    ('Medidor dañado',            4.0, 'Contador averiado o con lectura incorrecta'),
    ('Toma clandestina',          7.5, 'Conexión ilegal detectada a la red');

-- ─────────────────────────────────────────────────────────────
--  TABLA 4: reportes
--  Núcleo del sistema — cada incidencia ciudadana
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reportes (
    id                   SERIAL PRIMARY KEY,
    codigo_seguimiento   VARCHAR(20)      NOT NULL UNIQUE,
    id_usuario           INTEGER          REFERENCES usuarios(id) ON DELETE SET NULL,
    id_tipo              INTEGER          NOT NULL REFERENCES tipos_incidencia(id),
    id_zona              INTEGER          REFERENCES zonas(id) ON DELETE SET NULL,
    descripcion          TEXT,
    latitud              DECIMAL(10,7)    NOT NULL,
    longitud             DECIMAL(10,7)    NOT NULL,
    geom                 GEOMETRY(POINT, 4326),
    foto_url             VARCHAR(500),
    estado               estado_reporte   NOT NULL DEFAULT 'recibido',
    indice_prioridad     DECIMAL(5,2)     NOT NULL DEFAULT 0.0,
    nivel_urgencia       VARCHAR(20)      GENERATED ALWAYS AS (
                             CASE
                                 WHEN indice_prioridad >= 80 THEN 'critica'
                                 WHEN indice_prioridad >= 60 THEN 'alta'
                                 WHEN indice_prioridad >= 40 THEN 'media'
                                 ELSE 'baja'
                             END
                         ) STORED,
    id_operador_asignado INTEGER          REFERENCES usuarios(id) ON DELETE SET NULL,
    anonimo              BOOLEAN          NOT NULL DEFAULT FALSE,
    fecha_creacion       TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    fecha_actualizacion  TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    fecha_resolucion     TIMESTAMPTZ,
    archivado            BOOLEAN          NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_reportes_estado          ON reportes(estado);
CREATE INDEX idx_reportes_indice_prioridad ON reportes(indice_prioridad DESC);
CREATE INDEX idx_reportes_geom            ON reportes USING GIST(geom);
CREATE INDEX idx_reportes_zona            ON reportes(id_zona);
CREATE INDEX idx_reportes_operador        ON reportes(id_operador_asignado);
CREATE INDEX idx_reportes_fecha           ON reportes(fecha_creacion DESC);

-- Trigger: sincronizar geom y fecha_actualizacion en reportes
CREATE OR REPLACE FUNCTION sync_reporte_geom_fecha()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitud, NEW.latitud), 4326);
    NEW.fecha_actualizacion = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_reporte_geom_fecha
    BEFORE INSERT OR UPDATE ON reportes
    FOR EACH ROW EXECUTE FUNCTION sync_reporte_geom_fecha();

-- Función para generar código de seguimiento único AQP-YYYY-NNNNN
CREATE OR REPLACE FUNCTION generar_codigo_seguimiento()
RETURNS TRIGGER AS $$
DECLARE
    año     INTEGER;
    secuencia INTEGER;
BEGIN
    año := EXTRACT(YEAR FROM NOW());
    SELECT COALESCE(MAX(
        CAST(SPLIT_PART(codigo_seguimiento, '-', 3) AS INTEGER)
    ), 0) + 1
    INTO secuencia
    FROM reportes
    WHERE codigo_seguimiento LIKE 'AQP-' || año || '-%';

    NEW.codigo_seguimiento := 'AQP-' || año || '-' || LPAD(secuencia::TEXT, 5, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_generar_codigo
    BEFORE INSERT ON reportes
    FOR EACH ROW
    WHEN (NEW.codigo_seguimiento IS NULL OR NEW.codigo_seguimiento = '')
    EXECUTE FUNCTION generar_codigo_seguimiento();

-- ─────────────────────────────────────────────────────────────
--  TABLA 5: historial_reportes
--  Auditoría INMUTABLE de cada cambio de estado
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS historial_reportes (
    id              SERIAL PRIMARY KEY,
    id_reporte      INTEGER         NOT NULL REFERENCES reportes(id) ON DELETE CASCADE,
    estado_anterior estado_reporte,
    estado_nuevo    estado_reporte  NOT NULL,
    id_responsable  INTEGER         REFERENCES usuarios(id) ON DELETE SET NULL,
    comentario      TEXT,
    fecha           TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_historial_reporte ON historial_reportes(id_reporte);
CREATE INDEX idx_historial_fecha   ON historial_reportes(fecha DESC);

-- Trigger: registrar cambio de estado automáticamente en historial
CREATE OR REPLACE FUNCTION registrar_cambio_estado()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.estado IS DISTINCT FROM NEW.estado THEN
        INSERT INTO historial_reportes (id_reporte, estado_anterior, estado_nuevo, fecha)
        VALUES (NEW.id, OLD.estado, NEW.estado, NOW());
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_historial_estado
    AFTER UPDATE OF estado ON reportes
    FOR EACH ROW EXECUTE FUNCTION registrar_cambio_estado();

-- ─────────────────────────────────────────────────────────────
--  TABLA 6: criterios_prioridad
--  Pesos del motor IP — configurables sin tocar código
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS criterios_prioridad (
    id              SERIAL PRIMARY KEY,
    variable        VARCHAR(20)     NOT NULL UNIQUE,
    peso            DECIMAL(5,4)    NOT NULL CHECK (peso BETWEEN 0 AND 1),
    descripcion     TEXT,
    activo          BOOLEAN         NOT NULL DEFAULT TRUE,
    modificado_por  INTEGER         REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_mod       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Pesos por defecto según el documento
INSERT INTO criterios_prioridad (variable, peso, descripcion) VALUES
    ('G', 0.35, 'Gravedad del tipo de incidencia (1-10 según catálogo)'),
    ('D', 0.25, 'Densidad poblacional de la zona afectada'),
    ('T', 0.25, 'Tiempo sin atención (función logarítmica de horas transcurridas)'),
    ('R', 0.15, 'Recurrencia histórica del tipo en la zona (últimos 90 días)');

-- ─────────────────────────────────────────────────────────────
--  TABLA 7: nodos_red
--  Vértices del grafo hídrico G(V,E,W)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS nodos_red (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(120)    NOT NULL,
    id_zona     INTEGER         REFERENCES zonas(id) ON DELETE SET NULL,
    tipo        tipo_nodo       NOT NULL,
    latitud     DECIMAL(10,7)   NOT NULL,
    longitud    DECIMAL(10,7)   NOT NULL,
    geom        GEOMETRY(POINT, 4326),
    capacidad   DECIMAL(12,2)   NOT NULL DEFAULT 0,   -- litros/hora
    demanda     DECIMAL(12,2)   NOT NULL DEFAULT 0,   -- litros/hora requeridos
    activo      BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_nodos_geom ON nodos_red USING GIST(geom);
CREATE INDEX idx_nodos_tipo ON nodos_red(tipo);

CREATE OR REPLACE FUNCTION sync_nodo_geom()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitud, NEW.latitud), 4326);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_nodo_geom
    BEFORE INSERT OR UPDATE OF latitud, longitud ON nodos_red
    FOR EACH ROW EXECUTE FUNCTION sync_nodo_geom();

-- ─────────────────────────────────────────────────────────────
--  TABLA 8: aristas_red
--  Aristas del grafo hídrico (tuberías entre nodos)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aristas_red (
    id              SERIAL PRIMARY KEY,
    id_nodo_origen  INTEGER         NOT NULL REFERENCES nodos_red(id) ON DELETE CASCADE,
    id_nodo_destino INTEGER         NOT NULL REFERENCES nodos_red(id) ON DELETE CASCADE,
    capacidad       DECIMAL(12,2)   NOT NULL DEFAULT 0,   -- litros/hora máximo
    diametro        DECIMAL(6,2),                          -- centímetros
    longitud_m      DECIMAL(10,2),                         -- metros lineales de tubería
    estado          estado_arista   NOT NULL DEFAULT 'activa',
    CONSTRAINT no_autoreferencia CHECK (id_nodo_origen <> id_nodo_destino)
);

CREATE INDEX idx_aristas_origen  ON aristas_red(id_nodo_origen);
CREATE INDEX idx_aristas_destino ON aristas_red(id_nodo_destino);
CREATE INDEX idx_aristas_estado  ON aristas_red(estado);

-- ─────────────────────────────────────────────────────────────
--  TABLA 9: simulaciones
--  Registro persistente de cada simulación de falla ejecutada
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS simulaciones (
    id               SERIAL PRIMARY KEY,
    id_nodo_falla    INTEGER         REFERENCES nodos_red(id) ON DELETE SET NULL,
    id_arista_falla  INTEGER         REFERENCES aristas_red(id) ON DELETE SET NULL,
    nodos_afectados  JSONB           NOT NULL DEFAULT '[]',
    -- Estructura esperada:
    -- [{"id_nodo": 5, "nombre": "Col. Centro", "impacto": "sin_servicio",
    --   "reduccion_pct": 100, "rutas_alternativas": [...]}, ...]
    resultado_resumen TEXT,
    ejecutada_por    INTEGER         REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT falla_definida CHECK (
        id_nodo_falla IS NOT NULL OR id_arista_falla IS NOT NULL
    )
);

CREATE INDEX idx_simulaciones_fecha      ON simulaciones(fecha DESC);
CREATE INDEX idx_simulaciones_afectados  ON simulaciones USING GIN(nodos_afectados);

-- ─────────────────────────────────────────────────────────────
--  TABLA 10: asignaciones
--  Asignación formal de reportes a operadores
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS asignaciones (
    id               SERIAL PRIMARY KEY,
    id_reporte       INTEGER         NOT NULL REFERENCES reportes(id) ON DELETE CASCADE,
    id_operador      INTEGER         NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    id_admin_asigna  INTEGER         REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_asignacion TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    fecha_limite     TIMESTAMPTZ,
    notas            TEXT,
    activa           BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_asignaciones_reporte  ON asignaciones(id_reporte);
CREATE INDEX idx_asignaciones_operador ON asignaciones(id_operador);

-- ─────────────────────────────────────────────────────────────
--  TABLA 11: notificaciones
--  Alertas internas al ciudadano sobre sus reportes
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notificaciones (
    id              SERIAL PRIMARY KEY,
    id_usuario      INTEGER             NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo            tipo_notificacion   NOT NULL,
    mensaje         TEXT                NOT NULL,
    leida           BOOLEAN             NOT NULL DEFAULT FALSE,
    id_reporte_ref  INTEGER             REFERENCES reportes(id) ON DELETE CASCADE,
    fecha           TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notificaciones_usuario ON notificaciones(id_usuario, leida);
CREATE INDEX idx_notificaciones_fecha   ON notificaciones(fecha DESC);

-- ─────────────────────────────────────────────────────────────
--  TABLA 12: configuracion
--  Parámetros globales del sistema (SLA, umbrales, textos)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS configuracion (
    clave           VARCHAR(80)     PRIMARY KEY,
    valor           TEXT            NOT NULL,
    descripcion     TEXT,
    tipo_dato       VARCHAR(20)     NOT NULL DEFAULT 'string',  -- string, integer, float, boolean
    modificado_por  INTEGER         REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_mod       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Valores iniciales del sistema
INSERT INTO configuracion (clave, valor, descripcion, tipo_dato) VALUES
    ('sla_critica_horas',   '4',   'SLA para reportes críticos (IP≥80) en horas', 'integer'),
    ('sla_alta_horas',      '12',  'SLA para reportes de alta prioridad en horas', 'integer'),
    ('sla_media_horas',     '48',  'SLA para reportes de prioridad media en horas', 'integer'),
    ('sla_baja_dias',       '7',   'SLA para reportes de baja prioridad en días', 'integer'),
    ('max_reportes_operador', '15', 'Máximo de reportes activos por operador', 'integer'),
    ('foto_max_mb',         '5',   'Tamaño máximo de foto de evidencia en MB', 'integer'),
    ('recurrencia_dias',    '90',  'Ventana de días para calcular recurrencia histórica R', 'integer');

-- ─────────────────────────────────────────────────────────────
--  TABLA 13: sesiones
--  Registro de accesos al sistema para auditoría
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sesiones (
    id           SERIAL PRIMARY KEY,
    id_usuario   INTEGER         NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    ip           INET            NOT NULL,
    user_agent   TEXT,
    fecha_inicio TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    fecha_fin    TIMESTAMPTZ,
    activa       BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_sesiones_usuario ON sesiones(id_usuario);
CREATE INDEX idx_sesiones_activa  ON sesiones(activa, fecha_inicio DESC);

-- ─────────────────────────────────────────────────────────────
--  TABLA 14: auditoria
--  Log completo e inmutable de operaciones críticas
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS auditoria (
    id          SERIAL PRIMARY KEY,
    id_usuario  INTEGER         REFERENCES usuarios(id) ON DELETE SET NULL,
    modulo      VARCHAR(50)     NOT NULL,
    accion      VARCHAR(80)     NOT NULL,
    detalle     JSONB           NOT NULL DEFAULT '{}',
    ip          INET,
    fecha       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_auditoria_usuario ON auditoria(id_usuario);
CREATE INDEX idx_auditoria_modulo  ON auditoria(modulo, fecha DESC);
CREATE INDEX idx_auditoria_fecha   ON auditoria(fecha DESC);
CREATE INDEX idx_auditoria_detalle ON auditoria USING GIN(detalle);

-- ─────────────────────────────────────────────────────────────
--  VISTA: reportes_activos_con_prioridad
--  Vista conveniente para el dashboard de operadores
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW reportes_activos_con_prioridad AS
SELECT
    r.id,
    r.codigo_seguimiento,
    r.descripcion,
    r.latitud,
    r.longitud,
    r.estado,
    r.indice_prioridad,
    r.nivel_urgencia,
    r.anonimo,
    r.fecha_creacion,
    r.fecha_actualizacion,
    r.foto_url,
    -- Tipo de incidencia
    ti.nombre          AS tipo_nombre,
    ti.peso_gravedad   AS tipo_gravedad,
    -- Zona
    z.nombre           AS zona_nombre,
    z.poblacion        AS zona_poblacion,
    -- Ciudadano (puede ser NULL si es anónimo)
    u.nombre           AS ciudadano_nombre,
    u.email            AS ciudadano_email,
    -- Operador asignado
    op.nombre          AS operador_nombre,
    -- Horas sin atención
    EXTRACT(EPOCH FROM (NOW() - r.fecha_creacion)) / 3600.0 AS horas_sin_atencion
FROM reportes r
JOIN  tipos_incidencia ti ON ti.id = r.id_tipo
LEFT  JOIN zonas z         ON z.id  = r.id_zona
LEFT  JOIN usuarios u      ON u.id  = r.id_usuario
LEFT  JOIN usuarios op     ON op.id = r.id_operador_asignado
WHERE r.archivado = FALSE
  AND r.estado NOT IN ('cerrado');

-- ═══════════════════════════════════════════════════════════════
--  FIN DEL SCHEMA
-- ═══════════════════════════════════════════════════════════════
