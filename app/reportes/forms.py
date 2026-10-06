"""
app/reportes/forms.py
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Length, Optional


class ReporteForm(FlaskForm):
    id_tipo = SelectField("Tipo de problema", coerce=int, validators=[
        DataRequired(message="Selecciona el tipo de problema.")
    ])
    descripcion = TextAreaField("Descripción", validators=[
        Optional(),
        Length(max=1000)
    ])
    latitud  = HiddenField("Latitud",  validators=[DataRequired(message="Marca la ubicación en el mapa.")])
    longitud = HiddenField("Longitud", validators=[DataRequired(message="Marca la ubicación en el mapa.")])
    foto     = FileField("Foto de evidencia", validators=[
        Optional(),
        FileAllowed(["jpg", "jpeg", "png", "webp"], "Solo imágenes JPG, PNG o WEBP.")
    ])
    anonimo  = BooleanField("Enviar de forma anónima")