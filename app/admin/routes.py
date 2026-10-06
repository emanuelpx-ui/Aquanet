"""
app/admin/routes.py
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.auth.decorators import solo_administrador
from app.database import query_all, query_one, execute, execute_returning
import bcrypt

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
@login_required
@solo_administrador
def index():
    usuarios  = query_all("SELECT id, nombre, email, rol, activo FROM usuarios ORDER BY rol, nombre")
    nodos     = query_all("SELECT * FROM nodos_red ORDER BY tipo, nombre")
    aristas   = query_all("""
        SELECT a.*, n1.nombre AS origen, n2.nombre AS destino
        FROM aristas_red a
        JOIN nodos_red n1 ON n1.id = a.id_nodo_origen
        JOIN nodos_red n2 ON n2.id = a.id_nodo_destino
        ORDER BY n1.nombre
    """)
    return render_template("admin/index.html",
                           usuarios=usuarios, nodos=nodos, aristas=aristas)


# ── Usuarios ────────────────────────────────────────────────

@admin_bp.route("/usuario/nuevo", methods=["POST"])
@login_required
@solo_administrador
def usuario_nuevo():
    nombre   = request.form.get("nombre", "").strip()
    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    rol      = request.form.get("rol", "ciudadano")

    existente = query_one("SELECT id FROM usuarios WHERE email = %s", (email,))
    if existente:
        flash("Ese correo ya está registrado.", "danger")
        return redirect(url_for("admin.index"))

    hash_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()
    execute("""
        INSERT INTO usuarios (nombre, email, password_hash, rol, activo)
        VALUES (%s, %s, %s, %s, TRUE)
    """, (nombre, email, hash_pw, rol))
    flash(f"Usuario {nombre} creado correctamente.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/usuario/<int:user_id>/toggle", methods=["POST"])
@login_required
@solo_administrador
def usuario_toggle(user_id):
    usuario = query_one("SELECT activo, nombre FROM usuarios WHERE id = %s", (user_id,))
    if not usuario:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("admin.index"))
    nuevo = not usuario["activo"]
    execute("UPDATE usuarios SET activo = %s WHERE id = %s", (nuevo, user_id))
    estado = "activado" if nuevo else "desactivado"
    flash(f"Usuario {usuario['nombre']} {estado}.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/usuario/<int:user_id>/rol", methods=["POST"])
@login_required
@solo_administrador
def usuario_rol(user_id):
    nuevo_rol = request.form.get("rol")
    execute("UPDATE usuarios SET rol = %s WHERE id = %s", (nuevo_rol, user_id))
    flash("Rol actualizado.", "success")
    return redirect(url_for("admin.index"))


# ── Nodos de red ────────────────────────────────────────────

@admin_bp.route("/nodo/nuevo", methods=["POST"])
@login_required
@solo_administrador
def nodo_nuevo():
    lat = float(request.form.get("latitud", 0))
    lng = float(request.form.get("longitud", 0))

    if not (18.7 <= lat <= 19.4 and -98.6 <= lng <= -97.8):
        flash("Las coordenadas deben estar dentro del estado de Puebla.", "danger")
        return redirect(url_for("admin.index"))

    execute("""
        INSERT INTO nodos_red (nombre, tipo, latitud, longitud, capacidad, demanda, activo)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE)
    """, (
        request.form.get("nombre"),
        request.form.get("tipo"),
        lat, lng,
        float(request.form.get("capacidad", 0)),
        float(request.form.get("demanda", 0)),
    ))
    flash("Nodo agregado correctamente.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/nodo/<int:nodo_id>/eliminar", methods=["POST"])
@login_required
@solo_administrador
def nodo_eliminar(nodo_id):
    execute("DELETE FROM nodos_red WHERE id = %s", (nodo_id,))
    flash("Nodo eliminado.", "success")
    return redirect(url_for("admin.index"))


# ── Aristas de red ──────────────────────────────────────────

@admin_bp.route("/arista/nueva", methods=["POST"])
@login_required
@solo_administrador
def arista_nueva():
    execute("""
        INSERT INTO aristas_red (id_nodo_origen, id_nodo_destino, capacidad, estado)
        VALUES (%s, %s, %s, 'activa')
    """, (
        int(request.form.get("origen")),
        int(request.form.get("destino")),
        float(request.form.get("capacidad", 0)),
    ))
    flash("Tubería agregada correctamente.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/arista/<int:arista_id>/eliminar", methods=["POST"])
@login_required
@solo_administrador
def arista_eliminar(arista_id):
    execute("DELETE FROM aristas_red WHERE id = %s", (arista_id,))
    flash("Tubería eliminada.", "success")
    return redirect(url_for("admin.index"))

@admin_bp.route("/nodos/datos")
@login_required
@solo_administrador
def nodos_datos():
    from flask import jsonify
    nodos = query_all("SELECT id, nombre, tipo, latitud, longitud FROM nodos_red WHERE activo = TRUE")
    return jsonify([dict(n) for n in nodos])