"""
app/mapa/routes.py
"""
from flask import Blueprint, render_template
from flask_login import login_required

mapa_bp = Blueprint("mapa", __name__)


@mapa_bp.route("/")
@login_required
def index():
    return render_template("mapa/index.html")