from decimal import Decimal
import os
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from transform import transformar_datos


def get_db_config():
    """Obtiene la configuración de conexión a PostgreSQL exigiendo la variable de entorno PGPASSWORD."""
    password = os.getenv("PGPASSWORD")
    if not password:
        raise RuntimeError(
            "Falta la variable de entorno PGPASSWORD.\n"
            "Configúrala en PowerShell antes de ejecutar con:\n"
            '  $env:PGPASSWORD="TU_CONTRASEÑA"'
        )
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": os.getenv("PGPORT", "5432"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": password,
        "dbname": os.getenv("PGDATABASE", "chinook_dw"),
    }


def load_data(engine, data_dict: dict):
    """Carga los DataFrames transformados respetando estrictamente el orden referencial."""
    print("\n--- INICIANDO CARGA (L) EN POSTGRESQL ---")

    # Orden estricto: dimensiones independientes primero, tabla de hechos al final
    load_order = [
        ("dim_date", data_dict["dim_date"]),
        ("dim_employee", data_dict["dim_employee"]),
        ("dim_customer", data_dict["dim_customer"]),
        ("dim_track", data_dict["dim_track"]),
        ("fact_sales", data_dict["fact_sales"]),
    ]

    for table_name, df in load_order:
        print(f"Cargando {table_name} ({len(df)} registros)...")
        # Inserción en bloques con method='multi' para eficiencia
        df.to_sql(
            table_name,
            engine,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )
        print(f"  -> {table_name} cargada con éxito.")

    print("\n¡Carga completa finalizada con éxito!")


def verify_dw_data(engine):
    """Ejecuta consultas de control de calidad y cuadratura directamente en el Data Warehouse."""
    print("\n" + "=" * 70)
    print("CONTROL DE CALIDAD Y CUADRATURA DEL DATA WAREHOUSE")
    print("=" * 70)
    
    with engine.connect() as conn:
        # 1. Conteos de filas por tabla
        tablas = ["dim_date", "dim_employee", "dim_customer", "dim_track", "fact_sales"]
        for t in tablas:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"  * {t:<15}: {count:>6} filas")

        # 2. Verificación de playlist_count en dim_track
        tracks_con_playlist = conn.execute(
            text("SELECT COUNT(*) FROM dim_track WHERE playlist_count > 0")
        ).scalar()
        print(f"\n  * Tracks con playlist_count > 0: {tracks_con_playlist} de 3503")

        # 3. Suma total de ventas y conteo de hechos
        fact_count = conn.execute(text("SELECT COUNT(*) FROM fact_sales")).scalar()
        total_ventas = conn.execute(text("SELECT SUM(total_amount) FROM fact_sales")).scalar()
        print(f"  * Total acumulado en fact_sales : ${total_ventas:,.2f} (Esperado: $2,328.60)")

        # 4. Verificación de consistencia matemática
        inconsistencias = conn.execute(
            text("SELECT COUNT(*) FROM fact_sales WHERE total_amount <> (unit_price * quantity)")
        ).scalar()
        print(f"  * Inconsistencias matemáticas  : {inconsistencias}")

        # 5. Conciliación final frente a la fuente original
        print("\n" + "-" * 70)
        print("CONCILIACION FUENTE ORIGINAL vs. DATA WAREHOUSE")
        print("-" * 70)
        print(f"  Filas InvoiceLine.csv : 2240   | Filas fact_sales : {fact_count}")
        print(f"  Monto Fuente Total    : $2328.60 | Monto DW Total   : ${total_ventas}")
        print(f"  Errores Aritméticos   : 0        | Errores en DW    : {inconsistencias}")

        if (
            fact_count == 2240
            and total_ventas == Decimal("2328.60")
            and inconsistencias == 0
        ):
            print("\n>>> VALIDACION EXITOSA: El Data Warehouse quedó 100% consistente y cuadrado.")
        else:
            print("\n>>> ATENCION: Hay discrepancias en la cuadratura del Data Warehouse.")


def main():
    cfg = get_db_config()

    # Construcción segura de la URL con SQLAlchemy URL.create
    db_url = URL.create(
        drivername="postgresql+psycopg",
        username=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=int(cfg["port"]),
        database=cfg["dbname"],
    )
    engine = create_engine(db_url)

    # 1. Transformar datos en memoria (T)
    data_dict = transformar_datos()

    # 2. Cargar en PostgreSQL (L)
    load_data(engine, data_dict)

    # 3. Validar cuadratura final directamente contra PostgreSQL
    verify_dw_data(engine)


if __name__ == "__main__":
    main()
