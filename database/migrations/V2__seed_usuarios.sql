-- ═══════════════════════════════════════════════════════════════
--  V2__seed_usuarios.sql
--  Usuarios de demostración iniciales (Admin, Operador, Ciudadano)
-- ═══════════════════════════════════════════════════════════════

-- 1. Administrador (Contraseña: Admin1234)
INSERT INTO usuarios (nombre, email, password_hash, rol, activo, telefono, colonia)
VALUES (
    'Administrador del Sistema',
    'admin@aquanet.mx',
    '$2b$12$z6UKP3JfPJm2NPNZ3lilzeiOnSFuuy06lC6MP2SH4ZQL80DAEv9i6',
    'administrador',
    TRUE,
    '2220000001',
    'Centro Histórico'
)
ON CONFLICT (email) DO UPDATE
SET password_hash = EXCLUDED.password_hash,
    rol = 'administrador',
    activo = TRUE;

-- 2. Operador de Red (Contraseña: Operador1234)
INSERT INTO usuarios (nombre, email, password_hash, rol, activo, telefono, colonia)
VALUES (
    'Operador de Red Puebla',
    'operador@aquanet.mx',
    '$2b$12$.v7VBQ6iI9dOKKYgP91/F.fxzZC/lAxgDa5bN0VFBVWD0f5nZRK32',
    'operador',
    TRUE,
    '2220000002',
    'San Manuel'
)
ON CONFLICT (email) DO UPDATE
SET password_hash = EXCLUDED.password_hash,
    rol = 'operador',
    activo = TRUE;

-- 3. Ciudadano (Contraseña: Ciudadano1234)
INSERT INTO usuarios (nombre, email, password_hash, rol, activo, telefono, colonia)
VALUES (
    'Juan Ciudadano Ejemplo',
    'ciudadano@aquanet.mx',
    '$2b$12$cQFbTzwEt0Do2EwtzMI8ge2gRUyxZxGrglnJouPpK.CmsdBdaOfWS',
    'ciudadano',
    TRUE,
    '2220000003',
    'La Paz'
)
ON CONFLICT (email) DO UPDATE
SET password_hash = EXCLUDED.password_hash,
    rol = 'ciudadano',
    activo = TRUE;
