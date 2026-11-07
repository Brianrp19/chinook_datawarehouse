# Entorno local de desarrollo

## Preparación realizada

- Python 3.12.10 instalado para el usuario de Windows.
- Entorno virtual del proyecto creado en `.venv`.
- Archivo `.env` creado desde `.env.example` y excluido de Git.
- PostgreSQL 18 detectado y respondiendo en `127.0.0.1:5432`.

Los comandos siguientes se ejecutan desde la raíz del proyecto. Usar el Python del entorno evita depender del PATH o de la activación de PowerShell.

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/check_environment.py
```

Para reinstalar las dependencias desde el índice oficial:

```powershell
.\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple -r requirements.txt
```

## Configuración pendiente

1. Completar `PGPASSWORD` y `STG_PASSWORD` directamente en `.env`, sin compartirlas en el chat ni versionarlas.
2. Confirmar el host y puerto de Staging. No hubo respuesta en `127.0.0.1:5433` durante la comprobación inicial.
3. Iniciar o indicar la URL del servidor compartido de Prefect. No hubo respuesta en `http://127.0.0.1:4201/api/health` durante la comprobación inicial. Seguir `docs/comandos_prefect.md` para conservar la configuración del servidor compartido.
4. Ejecutar el comprobador y revisar los conteos existentes del DW antes de considerar una reconstrucción. No se ha ejecutado `sql/create_dw.sql`.

El comprobador usa transacciones de solo lectura, verifica las fuentes y los conteos del contrato, revisa permisos básicos del lector y consulta la salud de Prefect. No modifica tablas ni permisos; tampoco sustituye una auditoría completa de seguridad. Si hay comprobaciones pendientes o fallidas, termina con código 1.

## Auditoría del ETL

Cuando las conexiones estén verificadas:

```powershell
.\.venv\Scripts\python.exe src/etl_flow.py --no-load
```

Este modo extrae, valida y transforma en memoria sin cargar tablas del DW. Prefect registra la ejecución en su servidor. La preparación del entorno no implica ejecutar la carga completa ni reconstruir el esquema.
