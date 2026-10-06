"""
scripts/init_db.py
Inicializa la base de datos ejecutando el schema SQL.
Uso: python scripts/init_db.py
"""
import os
import sys
import psycopg2

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def init_db():
    """Ejecuta el schema SQL completo en la base de datos."""
    config = {
        "host":     os.getenv("DB_HOST", "localhost"),
        "port":     int(os.getenv("DB_PORT", 5432)),
        "dbname":   os.getenv("DB_NAME", "aquanet_puebla"),
        "user":     os.getenv("DB_USER", "aquanet_user"),
        "password": os.getenv("DB_PASSWORD", ""),
    }

    migrations_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "database", "migrations"
    )

    print(f"Conectando a PostgreSQL: {config['host']}:{config['port']}/{config['dbname']}")

    try:
        conn = psycopg2.connect(**config)
        conn.autocommit = True
        cur = conn.cursor()

        if not os.path.exists(migrations_dir):
            print(f"✗ Error: No se encontró la carpeta de migraciones en {migrations_dir}")
            sys.exit(1)

        archivos = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
        print(f"Aplicando {len(archivos)} migraciones desde {migrations_dir}...")
        for arch in archivos:
            ruta = os.path.join(migrations_dir, arch)
            print(f" • Ejecutando {arch}...")
            with open(ruta, "r", encoding="utf-8") as f:
                cur.execute(f.read())
        print("✓ Todas las migraciones aplicadas correctamente")

        # Verificar tablas creadas
        cur.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        tablas = [r[0] for r in cur.fetchall()]
        print(f"\n✓ Tablas en la BD ({len(tablas)}):")
        for t in tablas:
            print(f"   • {t}")

        cur.close()
        conn.close()
        print("\n✓ Base de datos lista para AquaNet Puebla (Usuarios semilla y datos demo cargados)")

    except psycopg2.OperationalError as e:
        print(f"✗ Error de conexión: {e}")
        print("\nVerifica que PostgreSQL esté corriendo y que las credenciales en .env sean correctas.")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error al aplicar schema: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_db()
