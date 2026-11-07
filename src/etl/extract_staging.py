"""Módulo de extracción desde PostgreSQL Staging (chinook_staging).

Conecta exclusivamente con el usuario lector acordado (chinook_stg_reader),
utilizando una única conexión y transacción REPEATABLE READ READ ONLY,
de acuerdo con el contrato contracts/staging_sources.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / ".env")

SOURCE_KEY_MAP = {
    "Album": "album",
    "Artist": "artist",
    "Customer": "customer",
    "Employee": "employee",
    "Genre": "genre",
    "Invoice": "invoice",
    "InvoiceLine": "invoice_line",
    "MediaType": "media_type",
    "Playlist": "playlist",
    "PlaylistTrack": "playlist_track",
    "Track": "track",
}

# Conversión estricta de tipos numéricos preservando campos de texto
TYPE_CONVERSIONS = {
    "album": {
        "int_cols": ["AlbumId", "ArtistId"]
    },
    "artist": {
        "int_cols": ["ArtistId"]
    },
    "customer": {
        "int_cols": ["CustomerId", "SupportRepId"]
    },
    "employee": {
        "int_cols": ["EmployeeId"],
        "nullable_int_cols": ["ReportsTo"]
    },
    "genre": {
        "int_cols": ["GenreId"]
    },
    "invoice": {
        "int_cols": ["InvoiceId", "CustomerId"],
        "float_cols": ["Total"]
    },
    "invoice_line": {
        "int_cols": ["InvoiceLineId", "InvoiceId", "TrackId", "Quantity"],
        "float_cols": ["UnitPrice"]
    },
    "media_type": {
        "int_cols": ["MediaTypeId"]
    },
    "playlist": {
        "int_cols": ["PlaylistId"]
    },
    "playlist_track": {
        "int_cols": ["PlaylistId", "TrackId"]
    },
    "track": {
        "int_cols": ["TrackId", "AlbumId", "MediaTypeId", "GenreId", "Milliseconds", "Bytes"],
        "float_cols": ["UnitPrice"]
    }
}


def get_staging_config() -> dict:
    """Lee y valida la configuración del lector de Staging desde .env."""
    required = ["STG_HOST", "STG_PORT", "STG_DATABASE", "STG_USER", "STG_PASSWORD"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise ValueError(
            f"Faltan variables de entorno requeridas para Staging: {', '.join(missing)}. "
            "Configure el acceso en .env según .env.example."
        )
    return {
        "host": os.getenv("STG_HOST"),
        "port": int(os.getenv("STG_PORT", "5433")),
        "dbname": os.getenv("STG_DATABASE", "chinook_staging"),
        "user": os.getenv("STG_USER", "chinook_stg_reader"),
        "password": os.getenv("STG_PASSWORD"),
        "sslmode": os.getenv("STG_SSLMODE", "prefer"),
    }


def extract_staging_data() -> Dict[str, pd.DataFrame]:
    """Extrae las 11 tablas de PostgreSQL Staging bajo REPEATABLE READ READ ONLY.

    Nunca recurre a CSV de forma silenciosa si Staging no está disponible.
    """
    cfg = get_staging_config()
    contract_path = PROJECT_DIR / "contracts" / "staging_sources.json"
    if not contract_path.exists():
        raise FileNotFoundError(
            f"No se encontró el contrato en {contract_path}. Verifique la configuración."
        )

    with open(contract_path, encoding="utf-8") as f:
        contract = json.load(f)

    db_url = URL.create(
        drivername="postgresql+psycopg",
        username=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=cfg["port"],
        database=cfg["dbname"],
        query={"sslmode": cfg["sslmode"]},
    )
    engine = create_engine(db_url)

    staging_data: Dict[str, pd.DataFrame] = {}

    try:
        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                for source in contract["sources"]:
                    source_name = source["source"]
                    key = SOURCE_KEY_MAP.get(source_name, source_name.lower())
                    query = text(source["query"])
                    df = pd.read_sql_query(query, connection, coerce_float=False)

                    # 1. Tratar cadenas vacías como NaN para compatibilidad con pandas
                    df = df.replace("", np.nan)

                    # 2. Aplicar conversiones numéricas según esquema
                    conversions = TYPE_CONVERSIONS.get(key, {})
                    for col in conversions.get("int_cols", []):
                        if col in df.columns:
                            df[col] = df[col].astype(int)
                    for col in conversions.get("nullable_int_cols", []):
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors="coerce")
                    for col in conversions.get("float_cols", []):
                        if col in df.columns:
                            df[col] = df[col].astype(float)

                    staging_data[key] = df
    except Exception as e:
        raise ConnectionError(
            f"Error crítico al extraer datos desde PostgreSQL Staging ({cfg['host']}:{cfg['port']}/{cfg['dbname']}): {e}"
        ) from e
    finally:
        engine.dispose()

    # Validar que se extrajeron exactamente las 11 tablas y 15.607 registros
    total_records = sum(len(df) for df in staging_data.values())
    if len(staging_data) != 11 or total_records != 15607:
        raise ValueError(
            f"Extracción incompleta o alterada: se obtuvieron {len(staging_data)} tablas y {total_records} registros (esperados: 11 tablas y 15607 registros)."
        )

    return staging_data


if __name__ == "__main__":
    data = extract_staging_data()
    print("Extracción de Staging exitosa:")
    for k, v in data.items():
        print(f"  - {k}: {len(v)} filas")
