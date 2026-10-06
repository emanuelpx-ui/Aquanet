"""
app/database.py
Conexion a PostgreSQL con psycopg2 - compatible con Windows.
"""
import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from flask import current_app, g

# Fix para Windows: evitar que psycopg2 lea archivos del sistema con caracteres especiales
os.environ["PGPASSFILE"] = ""
os.environ["PGSSLMODE"] = "disable"


def get_db_config(app=None):
    cfg = app.config if app else current_app.config
    return {
        "host":     cfg["DB_HOST"],
        "port":     cfg["DB_PORT"],
        "dbname":   cfg["DB_NAME"],
        "user":     cfg["DB_USER"],
        "password": cfg["DB_PASSWORD"],
    }


def get_db():
    if "db" not in g:
        config = get_db_config()
        g.db = psycopg2.connect(**config)
        g.db.autocommit = False
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        if error:
            db.rollback()
        db.close()


@contextmanager
def get_cursor(cursor_factory=psycopg2.extras.RealDictCursor):
    conn = get_db()
    cur = conn.cursor(cursor_factory=cursor_factory)
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def query_one(sql, params=None):
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def query_all(sql, params=None):
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def execute(sql, params=None):
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def execute_returning(sql, params=None):
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def init_db(app):
    app.teardown_appcontext(close_db)