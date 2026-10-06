"""
app/auth/routes.py
Blueprint de autenticación — login, logout, registro, perfil.
"""
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, current_app
)
from flask_login import (
    login_user, logout_user, login_required, current_user
)
from app.auth.forms import LoginForm, RegistroForm, CambiarPasswordForm
from app.auth.models import Usuario
from app.database import execute, execute_returning, query_one
import bcrypt

auth_bp = Blueprint("auth", __name__, template_folder="../../templates/auth")


# ─────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_dashboard_por_rol())

    form = LoginForm()

    if form.validate_on_submit():
        usuario = Usuario.get_by_email(form.email.data)

        # Usuario no existe
        if not usuario:
            flash("Correo o contraseña incorrectos.", "danger")
            return render_template("auth/login.html", form=form)

        # Cuenta inactiva
        if not usuario.is_active:
            flash("Tu cuenta está desactivada. Contacta al administrador.", "warning")
            return render_template("auth/login.html", form=form)

        # Cuenta bloqueada
        if usuario.esta_bloqueado:
            flash(
                f"Cuenta bloqueada. Intenta de nuevo en {usuario.minutos_bloqueado} minutos.",
                "danger"
            )
            return render_template("auth/login.html", form=form)

        # Contraseña incorrecta
        if not usuario.verificar_password(form.password.data):
            max_intentos = current_app.config.get("MAX_LOGIN_ATTEMPTS", 5)
            lockout_min  = current_app.config.get("LOCKOUT_MINUTES", 15)
            usuario.registrar_intento_fallido(max_intentos, lockout_min)

            restantes = max_intentos - usuario.intentos_fallidos
            if restantes > 0:
                flash(f"Contraseña incorrecta. Te quedan {restantes} intento(s).", "danger")
            else:
                flash(f"Cuenta bloqueada por {lockout_min} minutos.", "danger")
            return render_template("auth/login.html", form=form)

        # Login exitoso
        usuario.limpiar_intentos()

        # Registrar sesión en BD
        _registrar_sesion(usuario.id)

        login_user(usuario, remember=form.recordarme.data,
                   duration=current_app.config["PERMANENT_SESSION_LIFETIME"])

        # Auditoría
        _auditar(usuario.id, "auth", "login_exitoso",
                 {"email": usuario.email, "rol": usuario.rol})

        flash(f"Bienvenido, {usuario.nombre.split()[0]}.", "success")

        # Redirigir al destino original o al dashboard según rol
        next_page = request.args.get("next")
        return redirect(next_page or _dashboard_por_rol())

    return render_template("auth/login.html", form=form)


# ─────────────────────────────────────────────
#  LOGOUT
# ─────────────────────────────────────────────
@auth_bp.route("/logout")
@login_required
def logout():
    _cerrar_sesion(current_user.id)
    _auditar(current_user.id, "auth", "logout", {"email": current_user.email})
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))


# ─────────────────────────────────────────────
#  REGISTRO
# ─────────────────────────────────────────────
@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(_dashboard_por_rol())

    form = RegistroForm()

    if form.validate_on_submit():
        nuevo = Usuario.crear(
            nombre   = form.nombre.data.strip(),
            email    = form.email.data.strip(),
            password = form.password.data,
            telefono = form.telefono.data or None,
            colonia  = form.colonia.data or None,
            rol      = "ciudadano",
        )
        if nuevo:
            _auditar(nuevo.id, "auth", "registro_nuevo",
                     {"email": nuevo.email})
            login_user(nuevo)
            flash("¡Cuenta creada! Bienvenido a AquaNet Puebla.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("Ocurrió un error al crear la cuenta. Intenta de nuevo.", "danger")

    return render_template("auth/registro.html", form=form)


# ─────────────────────────────────────────────
#  PERFIL
# ─────────────────────────────────────────────
@auth_bp.route("/perfil")
@login_required
def perfil():
    return render_template("auth/perfil.html", usuario=current_user)


# ─────────────────────────────────────────────
#  CAMBIAR CONTRASEÑA
# ─────────────────────────────────────────────
@auth_bp.route("/cambiar-password", methods=["GET", "POST"])
@login_required
def cambiar_password():
    form = CambiarPasswordForm()

    if form.validate_on_submit():
        if not current_user.verificar_password(form.password_actual.data):
            flash("La contraseña actual es incorrecta.", "danger")
            return render_template("auth/cambiar_password.html", form=form)

        nuevo_hash = bcrypt.hashpw(
            form.password_nueva.data.encode("utf-8"),
            bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        execute(
            "UPDATE usuarios SET password_hash = %s WHERE id = %s",
            (nuevo_hash, current_user.id)
        )
        _auditar(current_user.id, "auth", "cambio_password", {})
        flash("Contraseña actualizada correctamente.", "success")
        return redirect(url_for("auth.perfil"))

    return render_template("auth/cambiar_password.html", form=form)


# ─────────────────────────────────────────────
#  HELPERS PRIVADOS
# ─────────────────────────────────────────────
def _dashboard_por_rol():
    return url_for("dashboard.index")


def _registrar_sesion(user_id: int):
    ip = request.remote_addr or "0.0.0.0"
    ua = request.user_agent.string[:500] if request.user_agent else ""
    execute(
        "INSERT INTO sesiones (id_usuario, ip, user_agent) VALUES (%s, %s, %s)",
        (user_id, ip, ua)
    )


def _cerrar_sesion(user_id: int):
    execute(
        """UPDATE sesiones SET activa = FALSE, fecha_fin = NOW()
           WHERE id_usuario = %s AND activa = TRUE""",
        (user_id,)
    )


def _auditar(user_id, modulo: str, accion: str, detalle: dict):
    import json
    ip = request.remote_addr or "0.0.0.0"
    execute(
        "INSERT INTO auditoria (id_usuario, modulo, accion, detalle, ip) VALUES (%s,%s,%s,%s,%s)",
        (user_id, modulo, accion, json.dumps(detalle), ip)
    )
