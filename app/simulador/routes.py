"""
app/simulador/routes.py
"""
import json
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.auth.decorators import operador_o_admin
from app.simulador.models import (
    simular_falla_nodo, simular_falla_arista, guardar_simulacion
)
from app.database import query_all

simulador_bp = Blueprint("simulador", __name__)


@simulador_bp.route("/")
@login_required
@operador_o_admin
def index():
    nodos   = query_all("SELECT id, nombre, tipo FROM nodos_red WHERE activo = TRUE ORDER BY nombre")
    aristas = query_all("""
        SELECT a.id, n1.nombre AS origen, n2.nombre AS destino
        FROM aristas_red a
        JOIN nodos_red n1 ON n1.id = a.id_nodo_origen
        JOIN nodos_red n2 ON n2.id = a.id_nodo_destino
        WHERE a.estado = 'activa'
        ORDER BY n1.nombre
    """)
    historial = query_all("""
        SELECT s.*, u.nombre AS ejecutado_por_nombre
        FROM simulaciones s
        LEFT JOIN usuarios u ON u.id = s.ejecutada_por
        ORDER BY s.fecha DESC LIMIT 10
    """)
    return render_template("simulador/index.html",
                           nodos=nodos, aristas=aristas, historial=historial)


@simulador_bp.route("/nodo", methods=["POST"])
@login_required
@operador_o_admin
def simular_nodo():
    nodo_id = request.form.get("nodo_id", type=int)
    if not nodo_id:
        return jsonify({"error": "Selecciona un nodo."}), 400

    resultado = simular_falla_nodo(nodo_id)
    if "error" in resultado:
        return jsonify(resultado), 400

    guardar_simulacion(resultado, current_user.id)
    return jsonify(resultado)


@simulador_bp.route("/arista", methods=["POST"])
@login_required
@operador_o_admin
def simular_arista():
    arista_id = request.form.get("arista_id", type=int)
    if not arista_id:
        return jsonify({"error": "Selecciona una tubería."}), 400

    resultado = simular_falla_arista(arista_id)
    if "error" in resultado:
        return jsonify(resultado), 400

    guardar_simulacion(resultado, current_user.id)
    return jsonify(resultado)