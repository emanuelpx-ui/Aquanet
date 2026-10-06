"""
app/dashboard/routes.py
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.database import query_one, query_all

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    # ── Vista ciudadano ──────────────────────────────────────
    if current_user.es_ciudadano:
        mis_reportes = query_all("""
            SELECT r.*, ti.nombre AS tipo_nombre
            FROM reportes r
            JOIN tipos_incidencia ti ON ti.id = r.id_tipo
            WHERE r.id_usuario = %s AND r.archivado = FALSE
            ORDER BY r.fecha_creacion DESC LIMIT 5
        """, (current_user.id,))
        return render_template("dashboard/ciudadano.html",
                               mis_reportes=mis_reportes)

    # ── Vista admin/operador ─────────────────────────────────
    kpis = query_one("""
        SELECT
            COUNT(*) FILTER (WHERE estado NOT IN ('cerrado','resuelto'))     AS activos,
            COUNT(*) FILTER (WHERE nivel_urgencia = 'critica')               AS criticos,
            COUNT(*) FILTER (WHERE nivel_urgencia = 'alta')                  AS altos,
            COUNT(*) FILTER (WHERE fecha_creacion >= NOW() - INTERVAL '24h') AS ultimas_24h,
            COUNT(*) FILTER (WHERE estado = 'resuelto')                      AS resueltos,
            ROUND(AVG(indice_prioridad)::numeric, 1)                         AS ip_promedio
        FROM reportes WHERE archivado = FALSE
    """)

    por_estado = query_all("""
        SELECT estado, COUNT(*) AS total
        FROM reportes WHERE archivado = FALSE
        GROUP BY estado ORDER BY total DESC
    """)

    por_tipo = query_all("""
        SELECT ti.nombre AS tipo, COUNT(*) AS total
        FROM reportes r
        JOIN tipos_incidencia ti ON ti.id = r.id_tipo
        WHERE r.archivado = FALSE
        GROUP BY ti.nombre ORDER BY total DESC LIMIT 8
    """)

    por_dia = query_all("""
        SELECT DATE(fecha_creacion) AS dia, COUNT(*) AS total
        FROM reportes
        WHERE fecha_creacion >= NOW() - INTERVAL '7 days'
        GROUP BY dia ORDER BY dia
    """)

    criticos = query_all("""
        SELECT r.id, r.codigo_seguimiento, ti.nombre AS tipo_nombre,
               r.estado, r.indice_prioridad,
               ROUND(EXTRACT(EPOCH FROM (NOW() - r.fecha_creacion))/3600)::int AS horas
        FROM reportes r
        JOIN tipos_incidencia ti ON ti.id = r.id_tipo
        WHERE r.nivel_urgencia = 'critica'
          AND r.estado NOT IN ('resuelto','cerrado')
          AND r.archivado = FALSE
        ORDER BY r.indice_prioridad DESC LIMIT 10
    """)

    return render_template("dashboard/index.html",
                           kpis=kpis,
                           por_estado=por_estado,
                           por_tipo=por_tipo,
                           por_dia=por_dia,
                           criticos=criticos)