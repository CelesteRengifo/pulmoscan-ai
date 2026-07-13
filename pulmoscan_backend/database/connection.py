"""
PulmoScan AI — Conexión a base de datos
Soporta SQLite (desarrollo) y PostgreSQL (producción)
según la variable de entorno DATABASE_URL.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from .models import Base
from dotenv import load_dotenv
load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
#  URL de conexión
#  Desarrollo:  sqlite:///./pulmoscan.db          (por defecto)
#  Producción:  postgresql://user:pass@host/db    (via variable de entorno)
# ──────────────────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pulmoscan.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    # SQLite necesita este flag para funcionar con FastAPI (multithreading)
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,   # True para ver SQL en consola (debug)
)

# Habilitar foreign keys en SQLite
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Crea todas las tablas si no existen. Llamar al iniciar la app."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency de FastAPI para inyectar la sesión de BD.
    Uso:
        @app.get("/ruta")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
