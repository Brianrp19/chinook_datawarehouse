from contextlib import nullcontext
from decimal import Decimal
import os
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Connection
from src.etl.extract_staging import extract_staging_data
from src.etl.transform import transformar_datos
from src.validations.validar_integridad import validar_integridad
from src.validations.validar_calidad_negocio import validar_calidad_negocio
from src.validations.validar_modelo_dw import validar_modelo_dw


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
    # Carga los DataFrames transformados en PostgreSQL, respetando el orden de dependencia.
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


def comparar_tabla_dw(conn, tabla, esperado, clave):
    # Compara el conteo de filas en la tabla del Data Warehouse con el esperado.
    columnas = list(esperado.columns)
    seleccion = ", ".join(f'"{col}"' for col in columnas)

    actual = pd.read_sql_query(f'select {seleccion} from public."{tabla}"', conn, coerce_float=False)

    for nombre, df in [("Staging transformado", esperado), ("DW", actual)]:
        if df[clave].isna().any():
            raise ValueError(f"Valores nulos encontrados en la columna clave '{clave}' de {nombre}.")
        if df[clave].duplicated().any():
            raise ValueError(f"Valores duplicados encontrados en la columna clave '{clave}' de {nombre}.")

    esperado = esperado.sort_values(clave).reset_index(drop=True)
    actual = actual.sort_values(clave).reset_index(drop=True)


    columnas_decimales ={"unit_price", "total_amount","duration_seconds", "duration_minutes"}

    columnas_fecha = {"full_date", "birth_date", "hire_date"}

    for columna in columnas:
        for df in (esperado, actual):
            if columna in columnas_decimales:
                df[columna] = df[columna].map(
                    lambda valor: (None if pd.isna(valor) else Decimal(str(valor)))
                ) 
            elif columna in columnas_fecha:
                df[columna] = pd.to_datetime(
                    df[columna], errors="raise"
                ).dt.date
        try:
            pd.testing.assert_series_equal(
                esperado[columna], actual[columna], check_dtype=False, check_exact=True
            )
        except AssertionError as error:    
            raise ValueError(
                f"{tabla}: Los datos en la columna '{columna}' no coinciden entre el Staging transformado y el Data Warehouse. \n {error}"
            ) from error

        print(f"[OK] {tabla}: La columna '{columna}' coincide entre el Staging transformado y el Data Warehouse.")
    


def verify_dw_data(engine, source_data: dict | None = None):
    # Verifica la consistencia del Data Warehouse comparando con los datos fuente.
    if source_data is None:
        raise ValueError(
            "No se proporcionaron datos de referencia para la cuadratura. "
            "Se requiere un diccionario con los datos originales extraídos desde PostgreSQL Staging."
        )

    source_lines = source_data.get("invoice_line")
    if source_lines is None:
        source_lines = source_data.get("InvoiceLine")

    if source_lines is None:
        raise ValueError(
            "No se encontraron datos de referencia para 'InvoiceLine' o 'invoice_line' en el diccionario proporcionado."
        )
    
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

        esperado = transformar_datos(source_data)

        claves = {
            "dim_date": "date_key",
            "dim_employee": "employee_key",
            "dim_customer": "customer_key",
            "dim_track": "track_key",
            "fact_sales": "invoice_line_id",
        }

        for tabla, clave in claves.items():
            # Compara cada tabla del Data Warehouse con su correspondiente DataFrame transformado.
            comparar_tabla_dw(conn, tabla, esperado[tabla], clave)

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

    try:
        # 1. Extraer y validar datos de Staging
        staging_data = extract_staging_data()
        validar_integridad(staging_data)
        validar_calidad_negocio(staging_data)

        # 2. Transformar y validar modelo en memoria (T)
        dw_data = transformar_datos(staging_data)
        validar_modelo_dw(dw_data)

        # 3. Cargar y conciliar de forma transaccional atómica en PostgreSQL (L)
        with engine.begin() as conn:
            conn.execute(
                text("TRUNCATE fact_sales, dim_track, dim_customer, dim_employee, dim_date CASCADE;")
            )
            load_data(conn, dw_data)
            verify_dw_data(conn, staging_data)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
