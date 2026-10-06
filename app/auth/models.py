"""
app/auth/models.py
Modelo de Usuario compatible con Flask-Login.
Gestiona autenticación, roles y control de bloqueo.
"""
import bcrypt
from datetime import datetime, timezone
from flask_login import UserMixin
from app.database import query_one, execute, execute_returning


class Usuario(UserMixin):
    """
    Representa un usuario del sistema (ciudadano, operador o administrador).
    Compatible con Flask-Login — implementa is_authenticated, is_active, get_id.
    """

    def __init__(self, row: dict):
        self.id                  = row["id"]
        self.nombre              = row["nombre"]
        self.email               = row["email"]
        self.password_hash       = row["password_hash"]
        self.telefono            = row.get("telefono")
        self.curp                = row.get("curp")
        self.colonia             = row.get("colonia")
        self.rol                 = row["rol"]
        self._activo             = row["activo"]
        self.intentos_fallidos   = row["intentos_fallidos"]
        self.bloqueado_hasta     = row.get("bloqueado_hasta")
        self.fecha_registro      = row["fecha_registro"]
        self.ultimo_acceso       = row.get("ultimo_acceso")

    # ── Flask-Login ────────────────────────────────────────────

    @property
    def is_active(self):
        return self._activo

    def get_id(self):
        return str(self.id)

    # ── Verificación de contraseña ─────────────────────────────

    def verificar_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            self.password_hash.encode("utf-8"),
        )

    # ── Estado de bloqueo ─────────────────────────────────────

    @property
    def esta_bloqueado(self) -> bool:
        if not self.bloqueado_hasta:
            return False
        ahora = datetime.now(timezone.utc)
        if self.bloqueado_hasta.tzinfo is None:
            self.bloqueado_hasta = self.bloqueado_hasta.replace(tzinfo=timezone.utc)
        return ahora < self.bloqueado_hasta

    @property
    def minutos_bloqueado(self) -> int:
        if not self.esta_bloqueado:
            return 0
        ahora = datetime.now(timezone.utc)
        delta = self.bloqueado_hasta - ahora
        return max(0, int(delta.total_seconds() / 60))

    # ── Roles (checks convenientes) ───────────────────────────

    @property
    def es_ciudadano(self) -> bool:
        return self.rol == "ciudadano"

    @property
    def es_operador(self) -> bool:
        return self.rol == "operador"

    @property
    def es_administrador(self) -> bool:
        return self.rol == "administrador"

    @property
    def puede_gestionar_reportes(self) -> bool:
        return self.rol in ("operador", "administrador")

    # ── Métodos de clase (queries) ────────────────────────────

    @classmethod
    def get_by_id(cls, user_id: int):
        row = query_one(
            "SELECT * FROM usuarios WHERE id = %s AND activo = TRUE",
            (user_id,)
        )
        return cls(row) if row else None

    @classmethod
    def get_by_email(cls, email: str):
        row = query_one(
            "SELECT * FROM usuarios WHERE email = %s",
            (email.lower().strip(),)
        )
        return cls(row) if row else None

    @classmethod
    def crear(cls, nombre: str, email: str, password: str,
              telefono: str = None, colonia: str = None,
              curp: str = None, rol: str = "ciudadano"):
        """Crea un nuevo usuario con contraseña hasheada."""
        hash_pw = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=12),
        ).decode("utf-8")

        row = execute_returning(
            """
            INSERT INTO usuarios
                (nombre, email, password_hash, telefono, colonia, curp, rol)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (nombre, email.lower().strip(), hash_pw, telefono, colonia, curp, rol),
        )
        return cls(row) if row else None

    def registrar_intento_fallido(self, max_intentos: int = 5, lockout_min: int = 15):
        """Incrementa intentos fallidos y bloquea si supera el límite."""
        nuevos_intentos = self.intentos_fallidos + 1

        if nuevos_intentos >= max_intentos:
            execute(
                """
                UPDATE usuarios
                SET intentos_fallidos = %s,
                    bloqueado_hasta   = NOW() + (%s * INTERVAL '1 minute')
                WHERE id = %s
                """,
                (nuevos_intentos, lockout_min, self.id),
            )
        else:
            execute(
                "UPDATE usuarios SET intentos_fallidos = %s WHERE id = %s",
                (nuevos_intentos, self.id),
            )
        self.intentos_fallidos = nuevos_intentos

    def limpiar_intentos(self):
        """Resetea el contador de intentos fallidos tras login exitoso."""
        execute(
            """
            UPDATE usuarios
            SET intentos_fallidos = 0,
                bloqueado_hasta   = NULL,
                ultimo_acceso     = NOW()
            WHERE id = %s
            """,
            (self.id,),
        )

    def __repr__(self):
        return f"<Usuario {self.id} {self.email} [{self.rol}]>"
