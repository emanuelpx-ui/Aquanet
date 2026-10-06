"""
app/auth/forms.py
Formularios de autenticación con Flask-WTF.
Incluyen validaciones del lado servidor.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, Regexp, ValidationError, Optional
)
from app.database import query_one


class LoginForm(FlaskForm):
    email = StringField("Correo electrónico", validators=[
        DataRequired(message="El correo es obligatorio."),
        Email(message="Ingresa un correo válido."),
    ])
    password = PasswordField("Contraseña", validators=[
        DataRequired(message="La contraseña es obligatoria."),
    ])
    recordarme = BooleanField("Mantener sesión iniciada")


class RegistroForm(FlaskForm):
    nombre = StringField("Nombre completo", validators=[
        DataRequired(message="El nombre es obligatorio."),
        Length(min=3, max=120, message="El nombre debe tener entre 3 y 120 caracteres."),
    ])
    email = StringField("Correo electrónico", validators=[
        DataRequired(message="El correo es obligatorio."),
        Email(message="Ingresa un correo válido."),
        Length(max=180),
    ])
    telefono = StringField("Teléfono (opcional)", validators=[
        Optional(),
        Regexp(r"^\+?[\d\s\-]{7,20}$", message="Formato de teléfono inválido."),
    ])
    colonia = StringField("Colonia", validators=[
        Optional(),
        Length(max=120),
    ])
    password = PasswordField("Contraseña", validators=[
        DataRequired(message="La contraseña es obligatoria."),
        Length(min=8, message="La contraseña debe tener al menos 8 caracteres."),
    ])
    confirmar_password = PasswordField("Confirmar contraseña", validators=[
        DataRequired(message="Confirma tu contraseña."),
        EqualTo("password", message="Las contraseñas no coinciden."),
    ])

    def validate_email(self, field):
        """Verifica que el correo no esté ya registrado."""
        existente = query_one(
            "SELECT id FROM usuarios WHERE email = %s",
            (field.data.lower().strip(),)
        )
        if existente:
            raise ValidationError("Este correo ya está registrado. Intenta iniciar sesión.")


class CambiarPasswordForm(FlaskForm):
    password_actual = PasswordField("Contraseña actual", validators=[
        DataRequired(),
    ])
    password_nueva = PasswordField("Nueva contraseña", validators=[
        DataRequired(),
        Length(min=8, message="Mínimo 8 caracteres."),
    ])
    confirmar = PasswordField("Confirmar nueva contraseña", validators=[
        DataRequired(),
        EqualTo("password_nueva", message="Las contraseñas no coinciden."),
    ])
