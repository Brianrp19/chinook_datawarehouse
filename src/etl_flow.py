import sys
from pathlib import Path

# Asegurar que la carpeta src esté en sys.path para importaciones locales
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import os
import urllib.request
from dotenv import load_dotenv

PROJECT_DIR = SRC_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

# Comprobación estricta de la API de Prefect para evitar fallback silencioso en demostraciones
_standalone_mode = "--standalone" in sys.argv
_help_mode = "-h" in sys.argv or "--help" in sys.argv
_api_url = os.environ.get("PREFECT_API_URL")

if _standalone_mode:
    os.environ["PREFECT_API_URL"] = ""
elif _api_url and not _help_mode:
    try:
        urllib.request.urlopen(_api_url.rstrip("/") + "/health", timeout=1.0)
    except Exception as _e:
        raise ConnectionError(
            f"\n[ERROR PREFECT API]: No se pudo conectar al servidor compartido en {_api_url}.\n"
            "Para la demostración, inicie el servidor compartido en el puerto 4201:\n"
            r"  .\.venv\Scripts\prefect.exe server start --port 4201\n"
            "Para ejecución local aislada sin servidor compartido, utilice el parámetro --standalone."
        ) from _e

import argparse
from prefect import flow, task
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from etl.extract_staging import extract_staging_data
from etl.transform import transformar_datos
from etl.load import get_db_config, load_data, verify_dw_data
from validations.validar_integridad import validar_integridad
from validations.validar_calidad_negocio import validar_calidad_negocio
from validations.validar_modelo_dw import validar_modelo_dw


def get_engine():
    """Crea y retorna el engine SQLAlchemy conectado a chinook_dw."""
    cfg = get_db_config()
    db_url = URL.create(
        drivername="postgresql+psycopg",
        username=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=int(cfg["port"]),
        database=cfg["dbname"],
    )
    return create_engine(db_url)


@task(name="Extraer Staging", log_prints=True)
def task_extraer_staging() -> dict:
    """Extrae las 11 fuentes desde PostgreSQL Staging en una sola transacción REPEATABLE READ."""
    print("Iniciando tarea de extracción desde PostgreSQL Staging...")
    staging_data = extract_staging_data()
    total_filas = sum(len(df) for df in staging_data.values())
    print(f"Extracción completada: 11 tablas y {total_filas} registros.")
    return staging_data


@task(name="Validar Integridad", log_prints=True)
def task_validar_integridad(staging_data: dict) -> None:
    validar_integridad(staging_data)


@task(name="Validar Calidad y Reglas de Negocio", log_prints=True)
def task_validar_calidad_negocio(staging_data: dict) -> None:
    validar_calidad_negocio(staging_data)


@task(name="Transformar Datos", log_prints=True)
def task_transformar(staging_data: dict) -> dict:
    """Aplica las reglas de transformación dimensional sobre los datos extraídos de Staging."""
    print("Iniciando tarea de transformación de datos...")
    dw_data = transformar_datos(staging_data)
    validar_modelo_dw(dw_data)
    print("------------------------------------------------")
    print("Validacion del modelo DW completada sin errores.")
    print("------------------------------------------------")
    print("Transformación finalizada exitosamente.")
    return dw_data


@task(name="Cargar Data Warehouse", log_prints=True)
def task_cargar(dw_data: dict, staging_data: dict) -> bool:
    """Limpia y carga los datos transformados en PostgreSQL respetando el orden referencial."""
    engine = get_engine()

    try:
        # Vaciado previo para garantizar una carga por lotes limpia e idempotente
        print("Vaciando tablas del Data Warehouse antes de la carga")
        with engine.begin() as conn:
            conn.execute(
                text("TRUNCATE fact_sales, dim_track, dim_customer, dim_employee, dim_date CASCADE;")
            )

            print("Cargando dimensiones y ventas...")
            load_data(conn, dw_data)

            print("Validando antes de confirmar transacción...")
            # Reutiliza exactamente los mismos datos extraídos inicialmente en staging_data
            verify_dw_data(conn, staging_data)

            print("Transacción confirmada exitosamente.")
            return True
    finally:
        engine.dispose()


@task(name="Validar Data Warehouse", log_prints=True)
def task_validar(staging_data: dict | None = None) -> bool:
    """Ejecuta los controles de calidad, conteos y conciliación monetaria en PostgreSQL."""
    engine = get_engine()
    try:
        print("Ejecutando validación de cuadratura en el Data Warehouse...")
        verify_dw_data(engine, staging_data)
        return True
    finally:
        engine.dispose()


@flow(name="Chinook ETL Data Warehouse", log_prints=True)
def etl_chinook(load_dw: bool = True):
    """Flujo principal orquestado con Prefect para el Data Warehouse de Chinook."""
    # 0. Extracción única desde PostgreSQL Staging
    staging_data = task_extraer_staging()

    # 1. Validaciones previas en memoria sobre los datos de Staging
    task_validar_integridad(staging_data)
    task_validar_calidad_negocio(staging_data)

    # 2. Tarea de Transformación (T)
    dw_data = task_transformar(staging_data)

    # 3. Tarea de Carga y Validación (L) - Controlable para auditoría sin escritura
    if load_dw:
        task_cargar(dw_data, staging_data)
        task_validar(staging_data)
    else:
        print("\n[MODO AUDITORIA/SIN CARGA]: Extracción, validación y transformación completadas en memoria.")
        print("No se realizaron escrituras en PostgreSQL 18 chinook_dw.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flujo ETL Chinook Data Warehouse")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--run-once",
        action="store_true",
        help="Ejecutar una sola vez el flujo ETL completo (extracción Staging, validaciones, transformaciones y carga en PostgreSQL 18)",
    )
    mode_group.add_argument(
        "--no-load",
        action="store_true",
        help="Modo seguro de auditoría: ejecuta extracción Staging, validaciones y transformaciones en memoria (sin escribir en PostgreSQL 18)",
    )
    mode_group.add_argument(
        "--serve",
        action="store_true",
        help="Desplegar el flujo en modo servidor/agente persistente de Prefect (etl_chinook.serve)",
    )
    parser.add_argument(
        "--standalone",
        action="store_true",
        help="Permitir ejecución local aislada con servidor efímero si no se usa el servidor compartido",
    )
    args = parser.parse_args()

    if args.run_once:
        print("Iniciando ejecución individual única del ETL con carga completa...")
        etl_chinook(load_dw=True)
    elif args.no_load:
        print("Iniciando ejecución de prueba en modo seguro (sin escritura en DW)...")
        etl_chinook(load_dw=False)
    elif args.serve:
        print("Iniciando servicio persistente de Prefect (chinook-local)...")
        etl_chinook.serve(
            name="chinook-local",
            limit=1,
        )
    else:
        print("Especifique una opción: --run-once (ejecución única), --no-load (modo auditoría) o --serve (servidor)")
        parser.print_help()
