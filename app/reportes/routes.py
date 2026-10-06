"""
app/reportes/routes.py
"""
import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.reportes.forms import ReporteForm
from app.reportes.models import Reporte
from app.database import execute
from app.database import execute, query_all


reportes_bp = Blueprint("reportes", __name__)


def _guardar_foto(file):
    if not file or file.filename == "":
        return None
    filename = secure_filename(file.filename)
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    ruta = os.path.join(folder, filename)
    file.save(ruta)
    return f"uploads/{filename}"


@reportes_bp.route("/")
@login_required
def index():
    pagina   = request.args.get("pagina", 1, type=int)
    por_pagina = 10
    offset   = (pagina - 1) * por_pagina

    if current_user.es_administrador:
        reportes = Reporte.get_todos(limit=por_pagina, offset=offset)
        total    = Reporte.contar_todos()
    elif current_user.es_operador:
        reportes = Reporte.get_by_operador(current_user.id, limit=por_pagina, offset=offset)
        total    = Reporte.contar_por_operador(current_user.id)
    else:
        reportes = Reporte.get_by_usuario(current_user.id, limit=por_pagina, offset=offset)
        total    = Reporte.contar_por_usuario(current_user.id)

    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)

    return render_template("reportes/lista.html",
                           reportes=reportes,
                           pagina=pagina,
                           total_paginas=total_paginas)


@reportes_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    form = ReporteForm()
    form.id_tipo.choices = [
        (t["id"], t["nombre"]) for t in Reporte.get_tipos()
    ]
    if form.validate_on_submit():
        foto_url = _guardar_foto(form.foto.data)
        reporte = Reporte.crear(
            id_tipo     = form.id_tipo.data,
            latitud     = float(form.latitud.data),
            longitud    = float(form.longitud.data),
            descripcion = form.descripcion.data or None,
            id_usuario  = None if form.anonimo.data else current_user.id,
            foto_url    = foto_url,
            anonimo     = form.anonimo.data,
        )
        flash(f"Reporte creado. Tu código: {reporte['codigo_seguimiento']}", "success")
        return redirect(url_for("reportes.detalle", reporte_id=reporte["id"]))

    return render_template("reportes/nuevo.html", form=form)


@reportes_bp.route("/<int:reporte_id>")
@login_required
def detalle(reporte_id):
    reporte = Reporte.get_by_id(reporte_id)
    if not reporte:
        flash("Reporte no encontrado.", "danger")
        return redirect(url_for("reportes.index"))

    operadores = []
    if current_user.puede_gestionar_reportes:
        operadores = query_all("""
            SELECT id, nombre FROM usuarios
            WHERE rol IN ('operador','administrador') AND activo = TRUE
            ORDER BY nombre
        """)

    return render_template("reportes/detalle.html",
                           reporte=reporte, operadores=operadores)


@reportes_bp.route("/consultar", methods=["GET", "POST"])
def consultar():
    reporte = None
    codigo  = ""
    if request.method == "POST":
        codigo  = request.form.get("codigo", "").strip()
        reporte = Reporte.get_by_codigo(codigo)
        if not reporte:
            flash("No se encontró ningún reporte con ese código.", "warning")
    return render_template("reportes/consultar.html", reporte=reporte, codigo=codigo)


@reportes_bp.route("/<int:reporte_id>/estado", methods=["POST"])
@login_required
def cambiar_estado(reporte_id):
    if not current_user.puede_gestionar_reportes:
        flash("No tienes permiso para esto.", "danger")
        return redirect(url_for("reportes.detalle", reporte_id=reporte_id))

    nuevo_estado = request.form.get("nuevo_estado")
    reporte = Reporte.get_by_id(reporte_id)

    execute(
        "UPDATE reportes SET estado = %s WHERE id = %s",
        (nuevo_estado, reporte_id)
    )

    # Notificar al ciudadano si no es anónimo
    if reporte and not reporte["anonimo"] and reporte["id_usuario"]:
        estado_texto = nuevo_estado.replace("_", " ").capitalize()
        execute("""
            INSERT INTO notificaciones (id_usuario, tipo, mensaje, id_reporte_ref)
            VALUES (%s, 'cambio_estado', %s, %s)
        """, (
            reporte["id_usuario"],
            f"Tu reporte {reporte['codigo_seguimiento']} cambió a: {estado_texto}",
            reporte_id
        ))

    flash("Estado actualizado.", "success")
    return redirect(url_for("reportes.detalle", reporte_id=reporte_id))

@reportes_bp.route("/exportar")
@login_required
def exportar_csv():
    if not current_user.puede_gestionar_reportes:
        flash("No tienes permiso para exportar.", "danger")
        return redirect(url_for("reportes.index"))

    import csv
    import io
    from flask import Response

    reportes = query_all("""
        SELECT r.codigo_seguimiento, ti.nombre AS tipo, r.estado,
               r.nivel_urgencia, r.indice_prioridad, r.latitud, r.longitud,
               r.descripcion, r.anonimo, r.fecha_creacion, r.fecha_resolucion,
               u.nombre AS ciudadano, op.nombre AS operador,
               z.nombre AS zona
        FROM reportes r
        JOIN tipos_incidencia ti ON ti.id = r.id_tipo
        LEFT JOIN usuarios u  ON u.id  = r.id_usuario
        LEFT JOIN usuarios op ON op.id = r.id_operador_asignado
        LEFT JOIN zonas z     ON z.id  = r.id_zona
        WHERE r.archivado = FALSE
        ORDER BY r.fecha_creacion DESC
    """)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Código", "Tipo", "Estado", "Urgencia", "IP",
        "Latitud", "Longitud", "Descripción", "Anónimo",
        "Fecha creación", "Fecha resolución",
        "Ciudadano", "Operador", "Zona"
    ])
    for r in reportes:
        writer.writerow([
            r["codigo_seguimiento"], r["tipo"], r["estado"],
            r["nivel_urgencia"], r["indice_prioridad"],
            r["latitud"], r["longitud"], r["descripcion"] or "",
            "Sí" if r["anonimo"] else "No",
            r["fecha_creacion"].strftime("%d/%m/%Y %H:%M") if r["fecha_creacion"] else "",
            r["fecha_resolucion"].strftime("%d/%m/%Y %H:%M") if r["fecha_resolucion"] else "",
            r["ciudadano"] or "Anónimo", r["operador"] or "Sin asignar",
            r["zona"] or "Sin zona"
        ])

    output.seek(0)
    return Response(
        output.getvalue().encode("utf-8-sig"),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=reportes_aquanet.csv"}
    )

@reportes_bp.route("/<int:reporte_id>/asignar", methods=["POST"])
@login_required
def asignar_operador(reporte_id):
    if not current_user.puede_gestionar_reportes:
        flash("No tienes permiso.", "danger")
        return redirect(url_for("reportes.detalle", reporte_id=reporte_id))

    operador_id = request.form.get("operador_id", type=int)
    execute("""
        UPDATE reportes SET id_operador_asignado = %s, estado = 'asignado'
        WHERE id = %s
    """, (operador_id, reporte_id))

    execute("""
        INSERT INTO historial_reportes (id_reporte, estado_anterior, estado_nuevo, id_responsable, comentario)
        SELECT %s, estado, 'asignado', %s, 'Operador asignado'
        FROM reportes WHERE id = %s
    """, (reporte_id, current_user.id, reporte_id))

    flash("Operador asignado correctamente.", "success")
    return redirect(url_for("reportes.detalle", reporte_id=reporte_id))

@reportes_bp.route("/notificaciones/leer", methods=["POST"])
@login_required
def marcar_notificaciones():
    execute(
        "UPDATE notificaciones SET leida = TRUE WHERE id_usuario = %s",
        (current_user.id,)
    )
    return redirect(request.referrer or url_for("reportes.index"))