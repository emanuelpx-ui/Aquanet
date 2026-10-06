-- ═══════════════════════════════════════════════════════════════
--  V3__seed_demo_datos.sql
--  Datos de demostración para evaluación y presentación
--  (Zonas, Nodos del Grafo Hídrico, Tuberías y Reportes muestra)
-- ═══════════════════════════════════════════════════════════════

-- 1. ZONAS DE PUEBLA
INSERT INTO zonas (nombre, municipio, latitud, longitud, poblacion, nivel_riesgo_historico) VALUES
    ('Centro Histórico', 'Puebla', 19.0435, -98.1983, 12500, 3.5),
    ('Colonia La Paz',   'Puebla', 19.0552, -98.2321,  8500, 2.0),
    ('Angelópolis',      'Puebla', 19.0305, -98.2338,  9200, 1.5),
    ('San Manuel',       'Puebla', 19.0198, -98.2045, 14000, 4.0),
    ('Amalucan',         'Puebla', 19.0538, -98.1524, 11000, 2.8)
ON CONFLICT DO NOTHING;

-- 2. NODOS DE LA RED HÍDRICA (Grafo)
INSERT INTO nodos_red (nombre, id_zona, tipo, latitud, longitud, capacidad, demanda, activo) VALUES
    ('Depósito San Felipe (Fuente)',  2, 'deposito',     19.0760, -98.2120, 50000,     0, TRUE),
    ('Depósito La Calera (Fuente)',   4, 'deposito',     19.0180, -98.1720, 60000,     0, TRUE),
    ('Tanque Regulador La Paz',        2, 'distribucion', 19.0550, -98.2320, 25000,  5000, TRUE),
    ('Estación de Bombeo Loreto',      1, 'distribucion', 19.0570, -98.1870, 30000,  4000, TRUE),
    ('Sector Centro Histórico',        1, 'colonia',      19.0435, -98.1983, 15000, 12000, TRUE),
    ('Sector Angelópolis',             3, 'colonia',      19.0305, -98.2338, 12000,  9000, TRUE),
    ('Sector San Manuel',              4, 'colonia',      19.0198, -98.2045, 14000, 11000, TRUE)
ON CONFLICT DO NOTHING;

-- 3. ARISTAS / TUBERÍAS DE LA RED
-- Conectar San Felipe -> Tanque La Paz
INSERT INTO aristas_red (id_nodo_origen, id_nodo_destino, capacidad, diametro, longitud_m, estado)
SELECT n1.id, n2.id, 25000, 30.0, 3500.0, 'activa'
FROM nodos_red n1, nodos_red n2
WHERE n1.nombre = 'Depósito San Felipe (Fuente)' AND n2.nombre = 'Tanque Regulador La Paz'
  AND NOT EXISTS (SELECT 1 FROM aristas_red WHERE id_nodo_origen = n1.id AND id_nodo_destino = n2.id);

-- Conectar Tanque La Paz -> Sector Angelópolis
INSERT INTO aristas_red (id_nodo_origen, id_nodo_destino, capacidad, diametro, longitud_m, estado)
SELECT n1.id, n2.id, 12000, 20.0, 2800.0, 'activa'
FROM nodos_red n1, nodos_red n2
WHERE n1.nombre = 'Tanque Regulador La Paz' AND n2.nombre = 'Sector Angelópolis'
  AND NOT EXISTS (SELECT 1 FROM aristas_red WHERE id_nodo_origen = n1.id AND id_nodo_destino = n2.id);

-- Conectar La Calera -> Bombeo Loreto
INSERT INTO aristas_red (id_nodo_origen, id_nodo_destino, capacidad, diametro, longitud_m, estado)
SELECT n1.id, n2.id, 35000, 35.0, 4200.0, 'activa'
FROM nodos_red n1, nodos_red n2
WHERE n1.nombre = 'Depósito La Calera (Fuente)' AND n2.nombre = 'Estación de Bombeo Loreto'
  AND NOT EXISTS (SELECT 1 FROM aristas_red WHERE id_nodo_origen = n1.id AND id_nodo_destino = n2.id);

-- Conectar Bombeo Loreto -> Sector Centro Histórico
INSERT INTO aristas_red (id_nodo_origen, id_nodo_destino, capacidad, diametro, longitud_m, estado)
SELECT n1.id, n2.id, 20000, 25.0, 1800.0, 'activa'
FROM nodos_red n1, nodos_red n2
WHERE n1.nombre = 'Estación de Bombeo Loreto' AND n2.nombre = 'Sector Centro Histórico'
  AND NOT EXISTS (SELECT 1 FROM aristas_red WHERE id_nodo_origen = n1.id AND id_nodo_destino = n2.id);

-- Conectar Bombeo Loreto -> Sector San Manuel
INSERT INTO aristas_red (id_nodo_origen, id_nodo_destino, capacidad, diametro, longitud_m, estado)
SELECT n1.id, n2.id, 15000, 20.0, 2900.0, 'activa'
FROM nodos_red n1, nodos_red n2
WHERE n1.nombre = 'Estación de Bombeo Loreto' AND n2.nombre = 'Sector San Manuel'
  AND NOT EXISTS (SELECT 1 FROM aristas_red WHERE id_nodo_origen = n1.id AND id_nodo_destino = n2.id);

-- 4. REPORTES INICIALES DE DEMOSTRACIÓN (Para mostrar Dashboard, Mapa y Prioridades)
INSERT INTO reportes (codigo_seguimiento, id_usuario, id_tipo, id_zona, descripcion, latitud, longitud, estado, indice_prioridad, anonimo, id_operador_asignado)
SELECT
    'AQP-2026-00001',
    u.id,
    1, -- Fuga en tubería maestra
    1, -- Centro Histórico
    'Fuga masiva de agua sobre calle 5 de Mayo, afectando varios comercios.',
    19.0440,
    -98.1990,
    'en_atencion',
    88.50,
    FALSE,
    op.id
FROM usuarios u, usuarios op
WHERE u.email = 'ciudadano@aquanet.mx' AND op.email = 'operador@aquanet.mx'
ON CONFLICT (codigo_seguimiento) DO NOTHING;

INSERT INTO reportes (codigo_seguimiento, id_usuario, id_tipo, id_zona, descripcion, latitud, longitud, estado, indice_prioridad, anonimo)
SELECT
    'AQP-2026-00002',
    u.id,
    4, -- Baja presión severa
    2, -- La Paz
    'Baja presión constante desde hace dos días en toda la cuadra.',
    19.0545,
    -98.2315,
    'en_revision',
    64.20,
    FALSE
FROM usuarios u
WHERE u.email = 'ciudadano@aquanet.mx'
ON CONFLICT (codigo_seguimiento) DO NOTHING;

INSERT INTO reportes (codigo_seguimiento, id_usuario, id_tipo, id_zona, descripcion, latitud, longitud, estado, indice_prioridad, anonimo)
SELECT
    'AQP-2026-00003',
    NULL,
    2, -- Fuga en tubería menor
    4, -- San Manuel
    'Fuga ligera de banqueta en Av. San Claudio.',
    19.0205,
    -98.2030,
    'recibido',
    42.00,
    TRUE
ON CONFLICT (codigo_seguimiento) DO NOTHING;
