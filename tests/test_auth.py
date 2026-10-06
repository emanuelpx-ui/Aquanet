"""
tests/test_auth.py
Pruebas unitarias para el modelo de usuario y verificación de roles y seguridad.
"""
import unittest
from datetime import datetime, timezone, timedelta
import bcrypt
from app.auth.models import Usuario


class TestUsuarioModel(unittest.TestCase):

    def setUp(self):
        self.password_plana = "SuperSegura123!"
        self.password_hash = bcrypt.hashpw(
            self.password_plana.encode("utf-8"),
            bcrypt.gensalt(rounds=10)
        ).decode("utf-8")

        self.user_data = {
            "id": 1,
            "nombre": "Juan Pérez",
            "email": "juan@example.com",
            "password_hash": self.password_hash,
            "telefono": "2221234567",
            "curp": "PEPJ900101HPLNNN01",
            "colonia": "Centro",
            "rol": "ciudadano",
            "activo": True,
            "intentos_fallidos": 0,
            "bloqueado_hasta": None,
            "fecha_registro": datetime.now(timezone.utc),
            "ultimo_acceso": None,
        }

    def test_verificar_password_correcta(self):
        user = Usuario(self.user_data)
        self.assertTrue(user.verificar_password(self.password_plana))

    def test_verificar_password_incorrecta(self):
        user = Usuario(self.user_data)
        self.assertFalse(user.verificar_password("ContrasenaErronea"))

    def test_roles_ciudadano(self):
        user = Usuario(self.user_data)
        self.assertTrue(user.es_ciudadano)
        self.assertFalse(user.es_operador)
        self.assertFalse(user.es_administrador)
        self.assertFalse(user.puede_gestionar_reportes)

    def test_roles_operador_y_admin(self):
        op_data = self.user_data.copy()
        op_data["rol"] = "operador"
        op = Usuario(op_data)
        self.assertTrue(op.es_operador)
        self.assertTrue(op.puede_gestionar_reportes)

        admin_data = self.user_data.copy()
        admin_data["rol"] = "administrador"
        admin = Usuario(admin_data)
        self.assertTrue(admin.es_administrador)
        self.assertTrue(admin.puede_gestionar_reportes)

    def test_bloqueo_usuario(self):
        user = Usuario(self.user_data)
        self.assertFalse(user.esta_bloqueado)
        self.assertEqual(user.minutos_bloqueado, 0)

        # Simular bloqueo por 15 minutos en el futuro
        user.bloqueado_hasta = datetime.now(timezone.utc) + timedelta(minutes=15)
        self.assertTrue(user.esta_bloqueado)
        self.assertGreaterEqual(user.minutos_bloqueado, 14)


if __name__ == "__main__":
    unittest.main()
