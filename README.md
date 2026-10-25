# Chinook Data Warehouse & ETL Pipeline

**Autores:** Brian y Miguel
**Repositorio:** `chinook_datawarehouse` (Capa de Data Warehouse y Analítica)
**Proyecto Universitario:** Chinook Data Platform (Arquitectura Multicapa Staging → Data Warehouse → Excel)

---

## 1. Contexto y Arquitectura Global de Datos

Este repositorio implementa la capa de **Data Warehouse**, el modelado dimensional en estrella (*Star Schema*), las validaciones de calidad de datos y el pipeline ETL orquestado con **Prefect**.

El proyecto forma parte de una solución corporativa modular donde las responsabilidades están desacopladas en repositorios Git y bases de datos independientes:

```text
+-----------------------+
|  11 CSVs Originales   | (Datos fuente sin procesar)
+-----------------------+
            |
            v
+--------------------------------------------------------------+
|  REPOSITORIO INDEPENDIENTE: Staging                          |
|  - PostgreSQL 17.11 (Puerto 5433, chinook_staging)           |
|  - 11 tablas stg_* (15,607 registros originales en TEXT)     |
|  - Usuario lector restringido: chinook_stg_reader            |
+--------------------------------------------------------------+
            |
            | Extracción segura bajo contrato SQL (contracts/staging_sources.json)
            | Aislamiento transaccional: REPEATABLE READ READ ONLY
            v
+--------------------------------------------------------------+
|  NUESTRO REPOSITORIO: chinook_datawarehouse (Brian y Miguel) |
|  - Pipeline ETL en Python 3 + Prefect 3                      |
|  - Perfilado, transformaciones dimensionales y SCD Tipo 1    |
|  - Validaciones de negocio, integridad referencial y tipos   |
|  - Carga transaccional atómica con conciliación matemática   |
|  - PostgreSQL 18 (Puerto 5432, chinook_dw)                   |
+--------------------------------------------------------------+
            |
            | Conexión directa mediante Power Query (5 consultas)
            v
+--------------------------------------------------------------+
|  CAPA ANALÍTICA Y REPORTES: Microsoft Excel                  |
|  - ecxel/Chinook_Analisis_DataWarehouse.xlsx                 |
|  - Modelos tabulares, KPIs y Tablas Dinámicas                |
+--------------------------------------------------------------+
```

---

## 2. Modelo Dimensional (Star Schema)

* **Proceso de Negocio:** Análisis de ventas de pistas musicales digitales y facturación a clientes.
* **Grano:** Una fila por cada línea de detalle de factura (`InvoiceLine`).
* **Estrategia Dimensional:** SCD Tipo 1 (Slowly Changing Dimensions Tipo 1).
* **Restricción de Consistencia:** `total_amount = unit_price * quantity`.

### Diagrama del Modelo Estrella

```text
                      +-------------------+
                      |     dim_date      |
                      |  (1,826 registros)|
                      +-------------------+
                                |
     +-------------------+      |      +-------------------+
     |   dim_customer    |------+------|     dim_track     |
     |  (59 registros)   |      |      | (3,503 registros) |
     +-------------------+      |      +-------------------+
                                |
                      +-------------------+
                      |    fact_sales     |
                      |  (2,240 registros)|
                      |    $2,328.60      |
                      +-------------------+
                                |
                      +-------------------+
                      |   dim_employee    |
                      |   (8 registros)   |
                      +-------------------+
```

### Detalle de Dimensiones y Tabla de Hechos

1. **`fact_sales` (Tabla de Hechos - 2,240 registros, $2,328.60):**
   - Transacciones de venta al mayor nivel de detalle.
   - Claves foráneas hacia las 4 dimensiones (`date_id`, `customer_id`, `employee_id`, `track_id`).
   - Claves degeneradas operacionales (`invoice_id`, `invoice_line_id`).
   - Métricas aditivas (`unit_price`, `quantity`, `total_amount`).

2. **`dim_date` (1,826 registros):**
   - Calendario continuo de 5 años (2009-01-01 a 2013-12-31).
   - Atributos enriquecidos: año, trimestre, mes, día, día de la semana y bandera de fin de semana (`is_weekend`).

3. **`dim_customer` (59 registros):**
   - Atributos demográficos de clientes, nombre completo, empresa, ciudad, estado, país y código postal.

4. **`dim_employee` (8 registros):**
   - Plantilla de empleados con soporte técnico y resolución jerárquica de supervisores (`reports_to_name`).

5. **`dim_track` (3,503 registros):**
   - Desnormalización completa integrando `Track`, `Album`, `Artist`, `Genre`, `MediaType` y agregación de listas de reproducción (`playlist_count` desde `PlaylistTrack`).

### Reglas de Calidad y Validación
- **Integridad Referencial (`src/validar_integridad.py`):** Cero registros huérfanos entre hechos y dimensiones.
- **Calidad de Negocio (`src/validar_calidad_negocio.py`):** Precios mayores a cero, cantidades estrictamente positivas y consistencia aritmética exacta `total_amount == unit_price * quantity`.
- **Validación de Modelo (`src/validar_modelo_dw.py`):** Respeto de límites de cadenas VARCHAR, tipos de datos numéricos y ausencia de nulos en claves primarias.

---

## 3. Estructura del Repositorio

```text
chinook_datawarehouse/
├── contracts/
│   ├── README.md                      # Documentación del contrato de fuentes
│   └── staging_sources.json           # Contrato formal SQL de tablas de Staging
├── ecxel/
│   ├── Chinook_Analisis_DataWarehouse.xlsx  # Libro analítico definitivo (Power Query)
│   └── Book1.xlsx                     # Versión histórica original preservada
├── sql/
│   └── create_dw.sql                  # DDL de PostgreSQL 18: tablas, PKs, FKs e índices
├── src/
│   ├── extract_staging.py             # Extracción segura de Staging (REPEATABLE READ)
│   ├── transform.py                   # Transformación dimensional en memoria
│   ├── validar_integridad.py          # Validación de claves y relaciones
│   ├── validar_calidad_negocio.py     # Reglas de precios, cantidades y montos
│   ├── validar_modelo_dw.py           # Validaciones de esquema y tipos
│   ├── load.py                        # Carga atómica a PostgreSQL 18 y conciliación
│   └── etl_flow.py                    # Orquestador del pipeline en Prefect 3
├── .env.example                       # Plantilla de variables de conexión
├── .gitignore                         # Exclusión de entornos, credenciales y temporales
├── comandosPrefect.md                 # Guía operativa de comandos Prefect y Excel
├── plan_reorganizacion.md             # Plan de arquitectura y desacoplamiento
├── requirements.txt                   # Dependencias de Python fijadas
└── README.md                          # Documentación técnica principal
```

---

## 4. Instalación y Configuración

### Prerrequisitos
- **Python 3.11+** (probado con Python 3.13 / 3.12).
- **PostgreSQL 18** (destino Data Warehouse en `127.0.0.1:5432`).
- **PostgreSQL 17** (origen Staging en `127.0.0.1:5433` con base `chinook_staging`).
- **Microsoft Excel** (con soporte para Power Query).

### Paso 1: Configurar el Entorno Virtual
En la raíz del proyecto `chinook_datawarehouse`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 2: Configurar Variables de Entorno (`.env`)
Copiar la plantilla `.env.example` a `.env` y configurar las credenciales locales:

```powershell
Copy-Item .env.example .env
```

Contenido representativo de `.env` (sin contraseñas reales):
```ini
# PostgreSQL 18 - Chinook Data Warehouse (Destino)
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DATABASE=chinook_dw
PG_USER=postgres
PG_PASSWORD=TU_PASSWORD_AQUI

# PostgreSQL 17 - Chinook Staging (Origen - Solo Lectura)
STG_HOST=127.0.0.1
STG_PORT=5433
STG_DATABASE=chinook_staging
STG_USER=chinook_stg_reader
STG_PASSWORD=TU_PASSWORD_READER_AQUI

# Servidor Centralizado de Prefect
PREFECT_API_URL=http://127.0.0.1:4201/api
```

### Paso 3: Crear el Esquema en PostgreSQL 18
Crear la base de datos `chinook_dw` en PostgreSQL 18 y ejecutar el DDL:
```powershell
# Mediante psql o herramienta de administración:
psql -h 127.0.0.1 -p 5432 -U postgres -d chinook_dw -f sql/create_dw.sql
```

---

## 5. Orquestación y Ejecución con Prefect

El proyecto utiliza un servidor centralizado de **Prefect 3** que unifica el monitoreo de ambos proyectos (`Chinook Staging ETL` y `Chinook ETL Data Warehouse`) en un único dashboard:

### Paso 1: Iniciar el Servidor Compartido de Prefect (Puerto 4201)
El servidor centralizado se inicia desde el repositorio de **Staging** para compartir el almacenamiento persistente:

```powershell
cd "C:\Ruta\Hacia\Staging"

$env:PREFECT_HOME = "C:\Ruta\Compartida\prefect_shared"
$env:PREFECT_UI_API_URL = "http://127.0.0.1:4201/api"
$env:PREFECT_API_URL = "http://127.0.0.1:4201/api"
$env:PREFECT_SERVER_ANALYTICS_ENABLED = "false"

.\.venv\Scripts\prefect.exe server start --host 127.0.0.1 --port 4201 --analytics-off
```

### Paso 2: Ejecutar el Pipeline del Data Warehouse
Desde este repositorio (`chinook_datawarehouse`):

```powershell
cd "C:\Ruta\Hacia\chinook_datawarehouse"

# Modo Carga Completa (Extrae de Staging -> Transforma -> Carga en chinook_dw -> Concilia):
.\.venv\Scripts\python.exe src/etl_flow.py --run-once

# Modo Validación y Auditoría (Solo validación en memoria, sin escribir en chinook_dw):
.\.venv\Scripts\python.exe src/etl_flow.py --no-load

# Modo Servicio / Espera (Escucha ejecuciones programadas):
.\.venv\Scripts\python.exe src/etl_flow.py --serve
```

### Paso 3: Visualización en el Dashboard de Prefect
- Acceder desde el navegador a: [http://127.0.0.1:4201/](http://127.0.0.1:4201/)
- En la pestaña **Runs**, se registran todas las ejecuciones de los flujos de ambos repositorios con el detalle de tareas (`task_extraer_staging`, `task_transformar_dimensiones`, `task_cargar`, `task_validar`).
- *Nota:* En esta fase académica los flujos se ejecutan de forma directa e interactiva; la sección **Deployments** no está configurada en este servidor.

---

## 6. Resultados y Cuadratura Matemática Validada

Cada ejecución del ETL valida de forma estricta los registros extraídos desde Staging contra el resultado cargado en el Data Warehouse:

```text
======================================================================
CONTROL DE CALIDAD Y CUADRATURA DEL DATA WAREHOUSE
======================================================================
  * Registros fuente en Staging :  15,607 filas (11 tablas stg_*)
  * dim_date                    :   1,826 filas
  * dim_employee                :       8 filas
  * dim_customer                :      59 filas
  * dim_track                   :   3,503 filas
  * fact_sales                  :   2,240 filas

  * Tracks con playlist_count > 0: 3,503 de 3,503
  * Total acumulado en fact_sales: $2,328.60 (Esperado: $2,328.60)
  * Inconsistencias matemáticas  : 0
  * Claves foráneas huérfanas    : 0

----------------------------------------------------------------------
CONCILIACIÓN STAGING vs. DATA WAREHOUSE
----------------------------------------------------------------------
  Filas stg_invoice_line : 2,240     | Filas fact_sales : 2,240
  Monto Staging Total    : $2,328.60 | Monto DW Total   : $2,328.60
  Diferencia Aritmética  : $0.00     | Estado           : 100% CONSISTENTE

>>> VALIDACIÓN EXITOSA: El Data Warehouse quedó 100% consistente y cuadrado.
```

---

## 7. Capa de Visualización y Análisis en Microsoft Excel

El análisis de inteligencia de negocios se presenta a través de **Microsoft Excel**:

### Archivo Principal
```powershell
Start-Process ".\ecxel\Chinook_Analisis_DataWarehouse.xlsx"
```
*(El archivo `ecxel/Book1.xlsx` se conserva exclusivamente como respaldo histórico original).*

### Conexión del Modelo en Excel:
- **Motor:** **Power Query** conectado a PostgreSQL 18 (`127.0.0.1:5432`, base de datos `chinook_dw`).
- **Consultas Directas al Modelo:** Excel consume de forma individual las 5 tablas del modelo dimensional en estrella:
  1. `dim_date`
  2. `dim_customer`
  3. `dim_employee`
  4. `dim_track`
  5. `fact_sales`
- **Actualización:** Para refrescar los gráficos y tablas dinámicas con nuevos datos del Data Warehouse, seleccionar la pestaña **Datos → Actualizar todo** (*Refresh All*).
- **Vista Analítica Complementaria (`vw_ventas_excel`):** En PostgreSQL 18 se incluye la vista SQL `vw_ventas_excel` que desnormaliza el modelo estrella para consultas analíticas directas o exportaciones planas alternativas.
