"""
app/auth/decorators.py
Decoradores de autorización para proteger rutas por rol.
Uso:
    @login_required
    @rol_requerido("administrador")
    def mi_vista(): ...

    @login_required
    @roles_permitidos("operador", "administrador")
    def vista_compartida(): ...
"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def rol_requerido(rol: str):
    """
    Restringe el acceso a usuarios con exactamente el rol indicado.
    Devuelve 403 si el rol no coincide.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.rol != rol:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def roles_permitidos(*roles):
    """
    Restringe el acceso a usuarios cuyo rol esté en la lista.
    Devuelve 403 si el rol no está incluido.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.rol not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def solo_administrador(f):
    """Shortcut: solo administradores pueden acceder."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.es_administrador:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def operador_o_admin(f):
    """Shortcut: operadores y administradores."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.puede_gestionar_reportes:
            abort(403)
        return f(*args, **kwargs)
    return decorated
