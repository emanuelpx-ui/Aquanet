"""
app/reportes/models.py
"""
from app.database import query_one, query_all, execute_returning, execute


class Reporte:

    @classmethod
    def crear(cls, id_tipo, latitud, longitud, descripcion=None,
              id_usuario=None, id_zona=None, foto_url=None, anonimo=False):
        return execute_returning("""
            INSERT INTO reportes
                (id_tipo, latitud, longitud, descripcion,
                 id_usuario, id_zona, foto_url, anonimo, codigo_seguimiento)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '')
            RETURNING *
        """, (id_tipo, latitud, longitud, descripcion,
              id_usuario, id_zona, foto_url, anonimo))

    @classmethod
    def get_by_id(cls, reporte_id):
        return query_one("""
            SELECT r.*,
                   ti.nombre AS tipo_nombre,
                   z.nombre  AS zona_nombre,
                   u.nombre  AS ciudadano_nombre,
                   op.nombre AS operador_nombre
            FROM reportes r
            JOIN tipos_incidencia ti ON ti.id = r.id_tipo
            LEFT JOIN zonas z  ON z.id  = r.id_zona
            LEFT JOIN usuarios u  ON u.id  = r.id_usuario
            LEFT JOIN usuarios op ON op.id = r.id_operador_asignado
            WHERE r.id = %s
        """, (reporte_id,))

    @classmethod
    def get_by_codigo(cls, codigo):
        return query_one("""
            SELECT r.*,
                   ti.nombre AS tipo_nombre,
                   z.nombre  AS zona_nombre,
                   op.nombre AS operador_nombre
            FROM reportes r
            JOIN tipos_incidencia ti ON ti.id = r.id_tipo
            LEFT JOIN zonas z ON z.id = r.id_zona
            LEFT JOIN usuarios op ON op.id = r.id_operador_asignado
            WHERE r.codigo_seguimiento = %s
        """, (codigo.upper().strip(),))

    @classmethod
    def get_by_usuario(cls, user_id, limit=10, offset=0):
        return query_all("""
            SELECT r.*, ti.nombre AS tipo_nombre, op.nombre AS operador_nombre
            FROM reportes r
            JOIN tipos_incidencia ti ON ti.id = r.id_tipo
            LEFT JOIN usuarios op ON op.id = r.id_operador_asignado
            WHERE r.archivado = FALSE AND r.id_usuario = %s
            ORDER BY r.fecha_creacion DESC
            LIMIT %s OFFSET %s
        """, (user_id, limit, offset))

    @classmethod
    def contar_por_usuario(cls, user_id):
        r = query_one("SELECT COUNT(*) AS total FROM reportes WHERE archivado=FALSE AND id_usuario=%s", (user_id,))
        return r["total"] if r else 0

    @classmethod
    def get_by_operador(cls, operador_id, limit=10, offset=0):
        return query_all("""
            SELECT r.*, ti.nombre AS tipo_nombre,
                   u.nombre AS ciudadano_nombre, op.nombre AS operador_nombre
            FROM reportes r
            JOIN tipos_incidencia ti ON ti.id = r.id_tipo
            LEFT JOIN usuarios u  ON u.id  = r.id_usuario
            LEFT JOIN usuarios op ON op.id = r.id_operador_asignado
            WHERE r.archivado = FALSE AND r.id_operador_asignado = %s
            ORDER BY r.indice_prioridad DESC, r.fecha_creacion DESC
            LIMIT %s OFFSET %s
        """, (operador_id, limit, offset))

    @classmethod
    def contar_por_operador(cls, operador_id):
        r = query_one("SELECT COUNT(*) AS total FROM reportes WHERE archivado=FALSE AND id_operador_asignado=%s", (operador_id,))
        return r["total"] if r else 0

    @classmethod
    def get_todos(cls, limit=10, offset=0):
        return query_all("""
            SELECT r.*, ti.nombre AS tipo_nombre,
                   u.nombre AS ciudadano_nombre, op.nombre AS operador_nombre
            FROM reportes r
            JOIN tipos_incidencia ti ON ti.id = r.id_tipo
            LEFT JOIN usuarios u  ON u.id  = r.id_usuario
            LEFT JOIN usuarios op ON op.id = r.id_operador_asignado
            WHERE r.archivado = FALSE
            ORDER BY r.indice_prioridad DESC, r.fecha_creacion DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))

    @classmethod
    def contar_todos(cls):
        r = query_one("SELECT COUNT(*) AS total FROM reportes WHERE archivado=FALSE")
        return r["total"] if r else 0

    @classmethod
    def get_tipos(cls):
        return query_all(
            "SELECT id, nombre FROM tipos_incidencia WHERE activo=TRUE ORDER BY nombre"
        )