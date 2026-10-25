# Guía de Comandos - Prefect & ETL Chinook Data Warehouse

## 1. Iniciar Servidor Centralizado de Prefect (Puerto 4201)

El servidor centralizado se inicia desde el repositorio independiente **Staging**, utilizando su propio entorno virtual y el directorio de base de datos compartida:

```powershell
cd "C:\Users\brian\OneDrive\Documentos\Base de datos\Staging"

$env:PREFECT_HOME = "C:\Users\brian\OneDrive\Documentos\Base de datos\prefect_shared"
$env:PREFECT_UI_API_URL = "http://127.0.0.1:4201/api"
$env:PREFECT_API_URL = "http://127.0.0.1:4201/api"
$env:PREFECT_SERVER_ANALYTICS_ENABLED = "false"

.\.venv\Scripts\prefect.exe server start --host 127.0.0.1 --port 4201 --analytics-off
```

## 2. Ejecutar Flujo ETL de Data Warehouse

Desde la raíz del repositorio **chinook_datawarehouse**, conéctate al servidor compartido y ejecuta el flujo:

```powershell
cd "C:\Users\brian\OneDrive\Documentos\Base de datos\chinook_datawarehouse"

# Modo Carga Completa (Extrae de Staging -> Transforma -> Valida -> Carga DW -> Concilia):
.\.venv\Scripts\python.exe src/etl_flow.py --run-once

# Modo Validación y Auditoría (Solo validación en memoria, sin escribir en chinook_dw):
.\.venv\Scripts\python.exe src/etl_flow.py --no-load
```

## 3. Monitoreo en Dashboard Centralizado

- Abrir en el navegador: [http://127.0.0.1:4201/](http://127.0.0.1:4201/)
- En la sección **Runs**, se visualizan las ejecuciones y tareas de ambos proyectos:
  - `Chinook Staging ETL`
  - `Chinook ETL Data Warehouse`

## 4. Visualización y Análisis en Excel

El archivo principal de presentación analítica del proyecto es `Chinook_Analisis_DataWarehouse.xlsx` (el archivo `Book1.xlsx` se conserva exclusivamente como versión histórica original):

```powershell
Start-Process ".\ecxel\Chinook_Analisis_DataWarehouse.xlsx"
```

### Arquitectura de Conexión en Excel:
- **Motor**: Power Query conectado a PostgreSQL 18 (`127.0.0.1:5432`, base de datos `chinook_dw`).
- **Consultas del Modelo**: Excel integra cinco consultas directas correspondientes a las tablas del modelo dimensional en estrella:
  1. `dim_date` (1,826 registros)
  2. `dim_customer` (59 registros)
  3. `dim_employee` (8 registros)
  4. `dim_track` (3,503 registros)
  5. `fact_sales` (2,240 registros, $2,328.60)
- **Actualización**: En Excel, seleccionar la pestaña **Datos -> Actualizar todo** (*Refresh All*) para refrescar el modelo tabular y las tablas dinámicas.
- **Vista Analítica Adicional**: La base de datos incluye además la vista `vw_ventas_excel` como alternativa de consulta analítica directa y desnormalizada.
