"""
app/prioridad/routes.py
"""
from flask import Blueprint, jsonify
from flask_login import login_required
from app.prioridad.services import recalcular_todos_los_indices, calcular_ip
from app.database import query_all, execute
from flask import current_app

prioridad_bp = Blueprint("prioridad", __name__)


@prioridad_bp.route("/recalcular", methods=["POST"])
@login_required
def recalcular():
    """Recálculo manual desde el panel admin."""
    try:
        recalcular_todos_los_indices(current_app._get_current_object())
        return jsonify({"ok": True, "mensaje": "Índices recalculados correctamente."})
    except Exception as e:
        return jsonify({"ok": False, "mensaje": str(e)}), 500


@prioridad_bp.route("/datos")
@login_required
def datos():
    """Devuelve todos los reportes activos como GeoJSON para el mapa."""
    reportes = query_all("""
        SELECT r.id,
               r.codigo_seguimiento,
               r.latitud,
               r.longitud,
               r.estado,
               r.indice_prioridad,
               r.nivel_urgencia,
               r.anonimo,
               ti.nombre AS tipo_nombre,
               z.nombre  AS zona_nombre
        FROM reportes r
        JOIN tipos_incidencia ti ON ti.id = r.id_tipo
        LEFT JOIN zonas z ON z.id = r.id_zona
        WHERE r.archivado = FALSE
          AND r.estado NOT IN ('cerrado')
    """)

    features = []
    for r in reportes:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(r["longitud"]), float(r["latitud"])]
            },
            "properties": {
                "id":               r["id"],
                "codigo":           r["codigo_seguimiento"],
                "tipo":             r["tipo_nombre"],
                "zona":             r["zona_nombre"] or "Sin zona",
                "estado":           r["estado"],
                "ip":               float(r["indice_prioridad"]),
                "urgencia":         r["nivel_urgencia"],
            }
        })

    return jsonify({"type": "FeatureCollection", "features": features})