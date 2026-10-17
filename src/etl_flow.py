from prefect import flow, task
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from transform import transformar_datos
from load import get_db_config, load_data, verify_dw_data
from validar_integridad import validar_integridad
from validar_calidad_negocio import validar_calidad_negocio



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

@task(name="Validar Integridad", log_prints=True)
def task_validar_integridad():
    validar_integridad()
    
@task(name="Validar Calidad y Reglas de Negocio", log_prints=True)
def task_validar_calidad_negocio():
    validar_calidad_negocio()

@task(name="Transformar Datos", log_prints=True)
def task_transformar() -> dict:
    """Extrae las fuentes CSV y aplica las reglas de transformación dimensional."""
    print("Iniciando tarea de transformación de datos...")
    data_dict = transformar_datos()
    print("Transformación finalizada exitosamente.")
    return data_dict


@task(name="Cargar Data Warehouse", log_prints=True)
def task_cargar(data_dict: dict) -> bool:
    """Limpia y carga los datos transformados en PostgreSQL respetando el orden referencial."""
    engine = get_engine()

    try:
        # Vaciado previo para garantizar una carga por lotes limpia e idempotente
        print("Vaciando tablas del Data Warehouse antes de la carga")
        with engine.begin() as conn:
            conn.execute(
                text("TRUNCATE fact_sales, dim_track, dim_customer, dim_employee, dim_date CASCADE;")
            )

            print("cargando dimenciones y ventas")
            load_data(conn, data_dict)

            print("Validando antes de confirmar")
            verify_dw_data(conn)

            print("Transaccion confirmada existosa")
            return True
    finally:
        engine.dispose()

@task(name="Validar Data Warehouse", log_prints=True)
def task_validar() -> bool:
    """Ejecuta los controles de calidad, conteos y conciliación monetaria en PostgreSQL."""
    engine = get_engine()
    print("Ejecutando validación de cuadratura en el Data Warehouse...")
    verify_dw_data(engine)
    return True


@flow(name="Chinook ETL Data Warehouse", log_prints=True)
def etl_chinook():
    """Flujo principal orquestado con Prefect para el Data Warehouse de Chinook."""

    # Antes que todo hacer la validación de integridad referencial
    task_validar_integridad()
    # Luego validar la calidad y reglas de negocio antes de cargar los datos
    task_validar_calidad_negocio()

    # 1. Tarea de Transformación (T)
    datos = task_transformar()

    # 2. Tarea de Carga (L)
    task_cargar(datos)

    # 3. Tarea de Validación de Calidad
    task_validar()


if __name__ == "__main__":
    etl_chinook.serve(
        name="chinook-local",
        limit=1,
    )

