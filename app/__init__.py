"""
app/__init__.py
Factory de la aplicación Flask — AquaNet Puebla.
"""
import os
from flask import Flask
from flask_login import LoginManager
from config.settings import get_config
from app.database import init_db

login_manager = LoginManager()


def create_app(config_object=None):
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    cfg = config_object or get_config()
    app.config.from_object(cfg)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    init_db(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para acceder a esta página."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        from app.auth.models import Usuario
        return Usuario.get_by_id(int(user_id))

    _register_blueprints(app)

    if app.config.get("SCHEDULER_ENABLED"):
        _init_scheduler(app)

    _register_template_filters(app)
    _register_context_processors(app)

    return app


def _register_blueprints(app):
    from app.auth.routes      import auth_bp
    from app.reportes.routes  import reportes_bp
    from app.mapa.routes      import mapa_bp
    from app.prioridad.routes import prioridad_bp
    from app.simulador.routes import simulador_bp
    from app.dashboard.routes import dashboard_bp
    from app.admin.routes     import admin_bp

    app.register_blueprint(auth_bp,       url_prefix="/auth")
    app.register_blueprint(reportes_bp,   url_prefix="/reportes")
    app.register_blueprint(mapa_bp,       url_prefix="/mapa")
    app.register_blueprint(prioridad_bp,  url_prefix="/prioridad")
    app.register_blueprint(simulador_bp,  url_prefix="/simulador")
    app.register_blueprint(dashboard_bp,  url_prefix="/dashboard")
    app.register_blueprint(admin_bp,      url_prefix="/admin")


def _init_scheduler(app):
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.prioridad.services import recalcular_todos_los_indices
    import atexit

    scheduler = BackgroundScheduler()
    interval = app.config.get("PRIORITY_RECALC_INTERVAL_MINUTES", 60)
    scheduler.add_job(
        func=lambda: recalcular_todos_los_indices(app),
        trigger="interval",
        minutes=interval,
        id="recalculo_ip",
        replace_existing=True,
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))


def _register_template_filters(app):
    from datetime import datetime, timezone

    @app.template_filter("fecha_corta")
    def fecha_corta(dt):
        if not dt:
            return "—"
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%d/%m/%Y %H:%M")

    @app.template_filter("horas_transcurridas")
    def horas_transcurridas(dt):
        if not dt:
            return "—"
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        horas = int(delta.total_seconds() / 3600)
        if horas < 24:
            return f"{horas}h"
        dias = horas // 24
        return f"{dias}d {horas % 24}h"

    @app.template_filter("urgencia_badge")
    def urgencia_badge(nivel):
        colores = {
            "critica": "danger",
            "alta": "warning",
            "media": "info",
            "baja": "success",
        }
        return colores.get(nivel, "secondary")


def _register_context_processors(app):
    from flask_login import current_user

    @app.context_processor
    def globals_template():
        notificaciones_no_leidas = 0
        notificaciones_recientes = []
        if current_user.is_authenticated:
            from app.database import query_one, query_all
            result = query_one(
                "SELECT COUNT(*) AS total FROM notificaciones "
                "WHERE id_usuario = %s AND leida = FALSE",
                (current_user.id,)
            )
            notificaciones_no_leidas = result["total"] if result else 0
            notificaciones_recientes = query_all(
                "SELECT mensaje, fecha FROM notificaciones "
                "WHERE id_usuario = %s AND leida = FALSE "
                "ORDER BY fecha DESC LIMIT 5",
                (current_user.id,)
            )
        return {
            "notif_count": notificaciones_no_leidas,
            "notificaciones_recientes": notificaciones_recientes,
            "app_nombre": "AquaNet Puebla",
        }
