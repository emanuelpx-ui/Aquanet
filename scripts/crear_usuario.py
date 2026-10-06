"""
scripts/crear_usuario.py
Crea un usuario administrador de prueba en AquaNet Puebla.
Uso: python scripts/crear_usuario.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import bcrypt
import psycopg2

# ── Usuarios a crear ───────────────────────────────────────────
USUARIOS = [
    {
        "nombre":   "Administrador del Sistema",
        "email":    "admin@aquanet.mx",
        "password": "Admin1234",
        "rol":      "administrador"
    },
    {
        "nombre":   "Operador de Red Puebla",
        "email":    "operador@aquanet.mx",
        "password": "Operador1234",
        "rol":      "operador"
    },
    {
        "nombre":   "Juan Ciudadano Ejemplo",
        "email":    "ciudadano@aquanet.mx",
        "password": "Ciudadano1234",
        "rol":      "ciudadano"
    }
]
# ──────────────────────────────────────────────────────────────

def main():
    config = {
        "host":     os.getenv("DB_HOST", "localhost"),
        "port":     int(os.getenv("DB_PORT", 5434)),
        "dbname":   os.getenv("DB_NAME", "aquanet_puebla"),
        "user":     os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "12345"),
    }

    print(f"Conectando a PostgreSQL: {config['host']}:{config['port']}/{config['dbname']}")

    conn = psycopg2.connect(**config)
    conn.autocommit = True
    cur = conn.cursor()

    print("\n═════════════════════════════════════════════════════════════")
    print(" Sembredo de Usuarios de Demostración para Presentación")
    print("═════════════════════════════════════════════════════════════\n")

    for u in USUARIOS:
        cur.execute("SELECT id, email, rol FROM usuarios WHERE email = %s", (u["email"],))
        existente = cur.fetchone()
        hash_pw = bcrypt.hashpw(u["password"].encode(), bcrypt.gensalt(12)).decode()

        if existente:
            cur.execute("""
                UPDATE usuarios
                SET password_hash = %s, rol = %s, activo = TRUE,
                    intentos_fallidos = 0, bloqueado_hasta = NULL
                WHERE email = %s
            """, (hash_pw, u["rol"], u["email"]))
            print(f" ✓ Usuario actualizado: {u['email']} [{u['rol']}] (Contraseña: {u['password']})")
        else:
            cur.execute("""
                INSERT INTO usuarios (nombre, email, password_hash, rol, activo)
                VALUES (%s, %s, %s, %s, TRUE)
            """, (u["nombre"], u["email"], hash_pw, u["rol"]))
            print(f" ✓ Usuario creado: {u['email']} [{u['rol']}] (Contraseña: {u['password']})")

    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Credenciales listas para presentación / revisión:
  ----------------------------------------------------------
  1) Administrador:
     Email:      admin@aquanet.mx
     Password:   Admin1234
     Acceso:     Dashboard global, Gestión de usuarios, Nodos y Red

  2) Operador:
     Email:      operador@aquanet.mx
     Password:   Operador1234
     Acceso:     Asignación y atención de reportes, Simulador de Red

  3) Ciudadano:
     Email:      ciudadano@aquanet.mx
     Password:   Ciudadano1234
     Acceso:     Crear reporte ciudadano, Ver mis reportes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  URL de acceso: http://localhost:5000
""")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()