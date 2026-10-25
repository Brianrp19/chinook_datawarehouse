from decimal import Decimal
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Connection
from transform import transformar_datos
from contextlib import nullcontext


PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")


def get_db_config():
    """Obtiene la configuración PostgreSQL desde .env o el entorno.

    En Linux se usa por defecto el socket local y autenticación peer, por lo
    que no es necesario almacenar una contraseña en el proyecto.
    """
    password = os.getenv("PGPASSWORD")
    return {
        "host": os.getenv("PGHOST", "/var/run/postgresql"),
        "port": os.getenv("PGPORT", "5432"),
        "user": os.getenv("PGUSER", os.getenv("USER", "postgres")),
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


def verify_dw_data(engine, source_data: dict | None = None):
    """Ejecuta consultas de control de calidad y cuadratura directamente en el Data Warehouse."""

    # Cuadratura frente a los datos originales extraídos desde PostgreSQL Staging
    if source_data is not None:
        source_lines = source_data.get("InvoiceLine", source_data.get("invoice_line"))
    else:
        # Valores de referencia oficiales del contrato Chinook cuando no se suministran datos en memoria
        expected_count = 2240
        expected_total = Decimal("2328.60")
        source_lines = None

    if source_lines is not None:
        expected_count = len(source_lines)
        expected_total = sum(
            (
                Decimal(str(price)) * int(quantity)
                for price, quantity in zip(
                    source_lines["UnitPrice"],
                    source_lines["Quantity"],
                )
            ),
            Decimal("0"),
        )

    print("\n" + "=" * 70)
    print("CONTROL DE CALIDAD Y CUADRATURA DEL DATA WAREHOUSE")
    print("=" * 70)

    contexto = (
        nullcontext(engine) if isinstance(engine, Connection) else engine.begin()
    )

    with contexto as conn:
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
        total_ventas = conn.execute(
            text("SELECT COALESCE(SUM(total_amount), 0) FROM fact_sales")
        ).scalar()
        print(f"\n * total de acumulado den fact_sales : ${total_ventas} ")
        print(f"\n Esperado: ${expected_total}")

        # 4. Verificación de consistencia matemática
        inconsistencias = conn.execute(
            text("SELECT COUNT(*) FROM fact_sales WHERE total_amount <> (unit_price * quantity)")
        ).scalar()
        print(f"  * Inconsistencias matemáticas  : {inconsistencias}")

        # 5. Conciliación final frente a la fuente original
        print("\n" + "-" * 70)
        print("CONCILIACION FUENTE ORIGINAL vs. DATA WAREHOUSE")
        print("-" * 70)
        print(
            f"  Filas fuente : {expected_count} "
            f"| Filas DW : {fact_count}"
        )

        print(
            f"  Monto fuente : ${expected_total:,.2f} "
            f"| Monto DW : ${total_ventas:,.2f}"
        )
        print(f"  Inconsistencias matemáticas en DW : {inconsistencias}")


        errores = []
        if fact_count != expected_count:
            errores.append(
                f"filas : se esperaban {expected_count},"
                f"pero se encontraron {fact_count}"
            )

        if total_ventas != expected_total:
            errores.append(
                f"monto : se esperaban ${expected_total:,.2f},"
                f"pero se encontraron ${total_ventas:,.2f}"
            )

        if inconsistencias != 0:
            errores.append(
                f"inconsistencias matemáticas : se esperaban 0,"
                f"pero se encontraron {inconsistencias}"
            )

        if errores:
            raise ValueError(
                "ERROR DE VALIDACION DEL DATA WAREHOUSE:\n"
                + "\n".join(errores)
            )

        if not errores:
            print("\n¡Validación exitosa! El Data Warehouse está cuadrado y consistente con la fuente original.")


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
