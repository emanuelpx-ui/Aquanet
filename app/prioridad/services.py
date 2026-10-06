"""
app/prioridad/services.py
Motor de Priorización Multicriterio.
IP = (G × 0.35) + (D × 0.25) + (T × 0.25) + (R × 0.15)
"""
import math
import logging
from app.database import query_all, execute

logger = logging.getLogger(__name__)


def calcular_ip(reporte: dict) -> float:
    """
    Calcula el Índice de Prioridad para un reporte.
    Retorna valor en escala 0-100.
    """
    # G — Gravedad del tipo (ya está en escala 0-10)
    g = float(reporte.get("tipo_gravedad") or 0)

    # D — Densidad poblacional normalizada (0-10)
    poblacion = float(reporte.get("zona_poblacion") or 0)
    d = min((poblacion / 10000) * 10, 10)

    # T — Tiempo sin atención en horas (logarítmico, 0-10)
    horas = float(reporte.get("horas_sin_atencion") or 0)
    t = min(math.log1p(horas) / math.log1p(168) * 10, 10)

    # R — Recurrencia histórica (0-10)
    r = min(max(float(reporte.get("recurrencia") or 0), 0.0), 10.0)

    # Pesos del documento
    ip = (g * 0.35) + (d * 0.25) + (t * 0.25) + (r * 0.15)

    # Escalar a 0-100 (asegurando el rango 0-100)
    return round(min(max(ip * 10, 0.0), 100.0), 2)


def recalcular_todos_los_indices(app):
    """Llamado por APScheduler cada hora."""
    with app.app_context():
        try:
            logger.info("[IP] Iniciando recálculo...")
            reportes = query_all("""
                SELECT r.id,
                       ti.peso_gravedad AS tipo_gravedad,
                       z.poblacion      AS zona_poblacion,
                       EXTRACT(EPOCH FROM (NOW() - r.fecha_creacion)) / 3600.0 AS horas_sin_atencion,
                       (
                         SELECT COUNT(*) FROM reportes r2
                         WHERE r2.id_zona = r.id_zona
                           AND r2.id_tipo = r.id_tipo
                           AND r2.fecha_creacion >= NOW() - INTERVAL '90 days'
                           AND r2.id != r.id
                       ) AS recurrencia
                FROM reportes r
                JOIN tipos_incidencia ti ON ti.id = r.id_tipo
                LEFT JOIN zonas z ON z.id = r.id_zona
                WHERE r.archivado = FALSE
                  AND r.estado NOT IN ('resuelto', 'cerrado')
            """)

            for rep in reportes:
                ip = calcular_ip(rep)
                execute(
                    "UPDATE reportes SET indice_prioridad = %s WHERE id = %s",
                    (ip, rep["id"])
                )

            logger.info(f"[IP] {len(reportes)} reportes recalculados.")
        except Exception as e:
            logger.error(f"[IP] Error: {e}")