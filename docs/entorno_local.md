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

## Estado verificado el 12 de noviembre de 2026

Las conexiones de Staging y DW están configuradas y autenticadas. Las 11 fuentes
contienen 15.607 registros y el lector cumple los permisos comprobados de solo
lectura. Las 15 pruebas unitarias y `pip check` pasan con Python 3.13.17.

Se corrigió `.env` para usar `PREFECT_API_URL=http://127.0.0.1:4201/api` y se
eliminaron asignaciones de PowerShell que no son valores válidos de dotenv.
El servidor local conserva su estado en `.prefect/`, excluido de Git.

La ejecución real `origami-termite` terminó en `Completed`, con las seis tareas
completadas y conciliación de todas las columnas antes y después del commit:
1.826 fechas, 8 empleados, 59 clientes, 3.503 pistas y 2.240 líneas de venta;
total $2.328,60 y cero inconsistencias matemáticas.

## Arranque local y carga completa

Desde la raíz del repositorio:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_prefect.ps1
.\.venv\Scripts\python.exe scripts/check_environment.py
.\.venv\Scripts\python.exe src/etl_flow.py --run-once
```

El primer comando reutiliza la API si ya responde; de lo contrario inicia un
servidor en segundo plano en el puerto 4201. Los logs quedan en
`.prefect/server.stdout.log` y `.prefect/server.stderr.log`. Tras reiniciar Windows
se debe ejecutar nuevamente el comando de arranque; no se instaló un servicio
automático. Staging puede usar la misma API para compartir el dashboard.
La carga completa reemplaza las cinco tablas de forma transaccional.
No es necesario recrear el esquema existente.

Dashboard: http://127.0.0.1:4201

El comprobador usa transacciones de solo lectura, verifica las fuentes y los conteos del contrato, revisa permisos básicos del lector y consulta la salud de Prefect. No modifica tablas ni permisos; tampoco sustituye una auditoría completa de seguridad. Si hay comprobaciones pendientes o fallidas, termina con código 1.

## Auditoría del ETL

Cuando las conexiones estén verificadas:

```powershell
.\.venv\Scripts\python.exe src/etl_flow.py --no-load
```

Este modo extrae, valida y transforma en memoria sin cargar tablas del DW. Prefect registra la ejecución en su servidor. La preparación del entorno no implica ejecutar la carga completa ni reconstruir el esquema.

# comando para arrancar prefect
$env:PREFECT_HOME = "$PWD\.prefect"
$env:PREFECT_SERVER_DATABASE_CONNECTION_URL = "sqlite+aiosqlite:///$($PWD.Path.Replace('\','/'))/.prefect/prefect.db"
$env:PREFECT_API_DATABASE_CONNECTION_URL = $env:PREFECT_SERVER_DATABASE_CONNECTION_URL
prefect server start --host 127.0.0.1 --port 4201

