# Chinook Data Warehouse & ETL Pipeline

**Autores:** Brian y Miguel<br>
**Repositorio:** `chinook_datawarehouse` (Capa de Data Warehouse y Analítica de Negocio)<br>
**Proyecto Universitario:** Chinook Data Platform (Arquitectura Multicapa Staging → Data Warehouse → Excel)

---

## 1. Contexto y Arquitectura Global de Datos

Este repositorio implementa la capa central de **Data Warehouse**, el modelado dimensional en estrella (*Star Schema*), el control estricto de calidad de datos y el pipeline ETL orquestado con **Prefect 3**.

El sistema global Chinook está organizado de forma desacoplada en dos proyectos y dos motores de bases de datos independientes que comparten un servidor central de orquestación:

```text
+-----------------------+
|  11 CSVs Originales   | (Datos fuente originales: 15.607 registros)
+-----------------------+
            |
            v
+--------------------------------------------------------------+
|  REPOSITORIO 1: Staging (Equipo de Jeremy)                   |
|  - Ruta: C:\...\Base de datos\Staging                        |
|  - Motor: PostgreSQL 17 (Puerto 5433, base chinook_staging)  |
|  - 11 tablas stg_* (fieles al CSV, valores como TEXT)        |
|  - 1 tabla técnica de auditoría / metadatos                  |
|  - Usuario cargador: chinook_stg_loader                      |
|  - Usuario lector restringido: chinook_stg_reader            |
+--------------------------------------------------------------+
            |
            | Extracción segura bajo contrato SQL formal:
            | contracts/staging_sources.json
            | Transacción atómica: REPEATABLE READ READ ONLY
            v
+--------------------------------------------------------------+
|  REPOSITORIO 2: chinook_datawarehouse (Brian y Miguel)       |
|  - Ruta: C:\...\Base de datos\chinook_datawarehouse          |
|  - Extracción: src/etl/extract_staging.py (NO lee CSVs)      |
|  - Pipeline ETL en Python 3 + Prefect 3                      |
|  - Validaciones de negocio, integridad referencial y tipos   |
|  - Modelo dimensional en estrella (4 dimensiones + hechos)   |
|  - Carga transaccional atómica con conciliación matemática   |
|  - Motor: PostgreSQL 18 (Puerto 5432, base chinook_dw)       |
+--------------------------------------------------------------+
            |
            | Conexión directa mediante Power Query (5 consultas)
            v
+--------------------------------------------------------------+
|  CAPA ANALÍTICA Y REPORTES: Microsoft Excel                  |
|  - Archivo: excel/Chinook_Analisis_DataWarehouse.xlsx        |
|  - Modelo tabular, KPIs, Tablas Dinámicas y Gráficos         |
+--------------------------------------------------------------+
```

### Principios Fundamentales de la Arquitectura
1. **Desacoplamiento Estricto:** Staging y Data Warehouse residen en repositorios Git y carpetas de trabajo diferentes. Staging no aplica transformaciones dimensionales ni escribe en el DW; Data Warehouse no lee directamente de los archivos CSV ni modifica las tablas de Staging.
2. **Acceso Seguro por Contrato:** La extracción desde el Data Warehouse se rige por el contrato formal [`contracts/staging_sources.json`](contracts/staging_sources.json), utilizando exclusivamente el usuario de solo lectura `chinook_stg_reader`.
3. **Consistencia Transaccional:** La extracción lee las 11 fuentes dentro de una única transacción con nivel de aislamiento `REPEATABLE READ READ ONLY`, garantizando una fotografía temporal 100% coherente entre tablas relacionadas.
4. **Orquestación Unificada:** Ambos proyectos comparten un servidor de orquestación Prefect 3 (puerto `4201`), lo que permite auditar las ejecuciones de Staging y Data Warehouse desde una misma consola web.

---

## 2. Contrato de Fuentes y Extracción desde Staging

La extracción de datos es ejecutada por el módulo [`src/etl/extract_staging.py`](src/etl/extract_staging.py), el cual implementa las siguientes garantías técnicas:

* **Base de Datos Origen:** PostgreSQL 17 (`127.0.0.1:5433`, base `chinook_staging`).
* **Credenciales:** Usuario `chinook_stg_reader` configurado en el archivo `.env` mediante variables `STG_*`.
* **Modo Transaccional:**
  ```python
  with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
      with connection.begin():
          connection.execute(text("SET TRANSACTION READ ONLY"))
          # Lectura consecutiva de las 11 tablas stg_*
  ```
* **Contrato SQL ([`contracts/staging_sources.json`](contracts/staging_sources.json)):**
  - Define las consultas canónicas explícitas ordenadas por `"CSV_ROW_NUMBER"`.
  - Excluye columnas técnicas del cálculo de negocio.
  - Especifica los tipos de datos destino y la política de tratamiento de campos vacíos (conversión controlada de `""` a `NaN` en memoria para compatibilidad analítica).
  - **Sin Fallback a CSV:** El sistema falla explícitamente si Staging no está disponible; nunca recurre de forma silenciosa a archivos CSV locales.

### Fuentes Extraídas de Staging (11 Tablas, 15.607 Registros)
| Fuente Staging | Tabla PostgreSQL 17 | Registros Esperados | Grano / Propósito en Staging |
|---|---|:---:|---|
| `Album` | `stg_album` | 347 | Catálogo de álbumes musicales |
| `Artist` | `stg_artist` | 275 | Catálogo de artistas e intérpretes |
| `Customer` | `stg_customer` | 59 | Clientes registrados y ubicación |
| `Employee` | `stg_employee` | 8 | Estructura organizacional y jerarquía |
| `Genre` | `stg_genre` | 25 | Géneros musicales |
| `Invoice` | `stg_invoice` | 412 | Cabeceras de facturación |
| `InvoiceLine` | `stg_invoice_line` | 2.240 | Detalle de líneas de venta ($2.328,60) |
| `MediaType` | `stg_media_type` | 5 | Formatos de audio y video digital |
| `Playlist` | `stg_playlist` | 18 | Listas de reproducción |
| `PlaylistTrack` | `stg_playlist_track` | 8.715 | Asociación muchos-a-muchos listas y pistas |
| `Track` | `stg_track` | 3.503 | Canciones, duración, tamaño y precios |
| **Total Staging** | **11 tablas fuente** | **15.607** | **Registros originales preservados** |

---

## 3. Modelo Dimensional (Star Schema)

* **Proceso de Negocio:** Análisis de ventas de pistas musicales digitales, desempeño por cliente, soporte de empleados y consumo por formatos/géneros.
* **Grano:** Una fila por cada línea de detalle de factura (`InvoiceLine`).
* **Estrategia Dimensional:** SCD Tipo 1 (Slowly Changing Dimensions Tipo 1 - Sobreescritura directa sin histórico).
* **Motor de Destino:** PostgreSQL 18 (`127.0.0.1:5432`, base de datos `chinook_dw`).

```text
                      +-------------------+
                      |     dim_date      |
                      |  (1.826 registros)|
                      +-------------------+
                                |
     +-------------------+      |      +-------------------+
     |   dim_customer    |------+------|     dim_track     |
     |  (59 registros)   |      |      | (3.503 registros) |
     +-------------------+      |      +-------------------+
                                |
                      +-------------------+
                      |    fact_sales     |
                      |  (2.240 registros)|
                      |    $2.328,60      |
                      +-------------------+
                                |
                      +-------------------+
                      |   dim_employee    |
                      |   (8 registros)   |
                      +-------------------+
```

### Detalle de Dimensiones y Tabla de Hechos

1. **`fact_sales` (Tabla de Hechos — 2.240 registros, $2.328,60):**
   - Grano transaccional atómico al nivel de línea de venta.
   - Claves foráneas sustitutas hacia las cuatro dimensiones: `date_key`, `customer_key`, `employee_key`, `track_key`.
   - Claves degeneradas operacionales: `invoice_id`, `invoice_line_id`.
   - Métricas: `quantity` y `total_amount` (aditivas al grano de línea), junto con `unit_price` (precio unitario de venta).
   - Consistencia matemática garantizada: `total_amount = unit_price * quantity`.

2. **`dim_date` (1.826 registros):**
   - Calendario continuo de 5 años completos (2009-01-01 a 2013-12-31).
   - Atributos analíticos: `year`, `quarter`, `month`, `day`, `day_of_week`, `day_name`, `month_name` y bandera de fin de semana (`is_weekend`).

3. **`dim_customer` (59 registros):**
   - Atributos del cliente: nombre completo (`full_name`), empresa, dirección, ciudad, estado, país y código postal.
   - Preserva códigos postales internacionales con ceros iniciales y caracteres especiales.

4. **`dim_employee` (8 registros):**
   - Plantilla de colaboradores y representantes de soporte.
   - Resolución de jerarquía organizacional mediante auto-unión (`reports_to_name`) para determinar la cadena de mando.

5. **`dim_track` (3.503 registros):**
   - Desnormalización dimensional completa que fusiona: `Track`, `Album`, `Artist`, `Genre` y `MediaType`.
   - Métrica precalculada: `playlist_count` (número de apariciones en listas de reproducción obtenido desde `PlaylistTrack`).
   - Los 3.503 tracks cuentan con al menos una lista de reproducción asociada (`playlist_count > 0`).

---

## 4. Pipeline ETL, Validaciones y Pruebas Unitarias

El pipeline se organiza de forma modular en `src/etl/` y `src/validations/`, orquestado por [`src/etl_flow.py`](src/etl_flow.py):

```text
[extract_staging.py] -> [validar_integridad.py] -> [validar_calidad_negocio.py] -> [transform.py] -> [validar_modelo_dw.py] -> [load.py]
```

### Reglas de Calidad y Validación
- **Validación de Integridad Referencial ([`src/validations/validar_integridad.py`](src/validations/validar_integridad.py)):**
  Verifica que no existan claves foráneas huérfanas ni claves duplicadas/nulas en los datos extraídos de Staging (`CustomerId` en facturas, `SupportRepId` en clientes, `ReportsTo` en empleados, `TrackId` en líneas de venta).
- **Validación de Reglas de Negocio ([`src/validations/validar_calidad_negocio.py`](src/validations/validar_calidad_negocio.py)):**
  Comprueba que los precios unitarios sean estrictamente mayores a cero, cantidades enteras positivas, coherencia temporal de empleados y coincidencia entre la suma de líneas y los totales de cabecera de factura.
- **Validación del Esquema DW ([`src/validations/validar_modelo_dw.py`](src/validations/validar_modelo_dw.py)):**
  Audita en memoria antes de la carga las claves primarias, tipos enteros de 32/64 bits, límites `VARCHAR` del DDL y referencias entre `fact_sales` y las cuatro dimensiones.
- **Carga Transaccional y Conciliación ([`src/etl/load.py`](src/etl/load.py)):**
  - Ejecuta un vaciado previo idempotente:
    ```sql
    TRUNCATE fact_sales, dim_track, dim_customer, dim_employee, dim_date CASCADE;
    ```
  - Carga las dimensiones independientes en primer orden y la tabla de hechos al final.
  - Compara columna por columna cada tabla cargada contra la transformación esperada y realiza la conciliación matemática (`verify_dw_data`) dentro de la misma transacción antes de confirmar el `COMMIT`.

### Ejecución de Pruebas Unitarias y Diagnóstico
```powershell
# Suite de pruebas unitarias en memoria (transformaciones y rechazo de datos inválidos)
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# Verificación de entorno, puertos, contrato de Staging y estado de Prefect
.\.venv\Scripts\python.exe scripts/check_environment.py
```

---

## 5. Estructura del Repositorio

```text
chinook_datawarehouse/
├── contracts/
│   ├── README.md                          # Documentación del contrato de extracción
│   └── staging_sources.json               # Especificación formal JSON del contrato SQL
├── docs/
│   ├── README.md                          # Índice de documentación operativa
│   ├── comandos_prefect.md                # Guía operativa paso a paso para la exposición
│   ├── entorno_local.md                   # Preparación y diagnóstico del entorno local
│   └── historico/                         # Bitácoras, planes previos y respaldos del equipo
├── drivers/
│   └── Npgsql-4.0.17.msi                  # Instalador del conector PostgreSQL para Excel
├── excel/
│   └── Chinook_Analisis_DataWarehouse.xlsx  # Libro analítico definitivo conectado a PG18
├── scripts/
│   ├── check_environment.py               # Verificador de conexiones, permisos y contrato
│   └── explorar_datos.py                  # Exploración y perfilado de las 11 tablas Staging
├── sql/
│   ├── create_dw.sql                      # DDL de PostgreSQL 18: tablas, índices y PK/FK
│   ├── vista_excel.sql                    # Vista desnormalizada vw_ventas_excel
│   └── consultas.sql                      # Consultas analíticas multidimensionales OLAP
├── src/
│   ├── etl_flow.py                        # Orquestador principal del flujo con Prefect 3
│   ├── etl/
│   │   ├── extract_staging.py             # Extracción segura de PostgreSQL 17 (REPEATABLE READ)
│   │   ├── transform.py                   # Transformación dimensional al Star Schema
│   │   └── load.py                        # Carga atómica a PostgreSQL 18 y conciliación
│   └── validations/
│       ├── validar_integridad.py          # Validación de claves y relaciones de Staging
│       ├── validar_calidad_negocio.py     # Reglas de negocio (precios, cantidades, totales)
│       └── validar_modelo_dw.py           # Validación de tipos, rangos y longitudes del DW
├── tests/
│   ├── helpers.py                         # Fixtures sintéticos de referencia para pruebas
│   ├── test_transform.py                  # Pruebas unitarias del modelo dimensional
│   └── test_validations.py                # Pruebas unitarias de controles y casos inválidos
├── .env.example                           # Plantilla pública de variables de entorno
├── .gitignore                             # Exclusión de entornos (.venv), secretos (.env) y temporales
├── requirements.txt                       # Dependencias de Python fijadas
└── README.md                              # Documentación técnica principal
```

---

## 6. Instalación y Configuración

### Prerrequisitos
- **Python 3.11+** (recomendado Python 3.12 o 3.13 con soporte para Prefect 3).
- **PostgreSQL 18** (puerto `5432`, base de datos destino `chinook_dw`).
- **PostgreSQL 17** (puerto `5433`, base de datos origen `chinook_staging`, previamente provisionada).
- **Microsoft Excel** (con soporte para Power Query y controlador PostgreSQL / Npgsql).

### Paso 1: Configurar el Entorno Virtual
Desde una terminal PowerShell en la raíz de `chinook_datawarehouse`:
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

Contenido de referencia de `.env` (sin credenciales reales):
```ini
# PostgreSQL 18 - Chinook Data Warehouse (Destino de Carga)
PGHOST=127.0.0.1
PGPORT=5432
PGDATABASE=chinook_dw
PGUSER=postgres
PGPASSWORD=TU_PASSWORD_LOCAL

# PostgreSQL 17 - Chinook Staging (Origen de Extracción - Solo Lectura)
STG_HOST=127.0.0.1
STG_PORT=5433
STG_DATABASE=chinook_staging
STG_USER=chinook_stg_reader
STG_PASSWORD=TU_PASSWORD_READER_LOCAL
STG_SSLMODE=prefer

# Servidor Centralizado de Prefect (Compartido con Staging)
PREFECT_API_URL=http://127.0.0.1:4201/api
```

### Paso 3: Inicializar la Estructura en PostgreSQL 18
Si la base de datos `chinook_dw` es nueva, ejecutar el script DDL:
```powershell
psql -h 127.0.0.1 -p 5432 -U postgres -d chinook_dw -f sql/create_dw.sql
```
*(Nota: Si la base ya fue creada previamente, no es necesario ejecutar este paso).*

---

## 7. Orquestación y Ejecución con Prefect 3

El proyecto utiliza un servidor centralizado de **Prefect 3** que unifica el monitoreo de ambos proyectos (`Chinook Staging ETL` y `Chinook ETL Data Warehouse`) en un único dashboard:

* **Servidor Centralizado (Puerto 4201):** Se inicia una única vez desde el repositorio de **Staging** para compartir el almacenamiento persistente (`prefect_shared`).
* **Dashboard Web:** [http://127.0.0.1:4201](http://127.0.0.1:4201)

### Modalidades de Ejecución de este Data Warehouse

Desde la raíz de `chinook_datawarehouse`, con la variable `PREFECT_API_URL` apuntando al puerto 4201:

1. **Modo Seguro de Práctica / Auditoría (`--no-load`):**
   ```powershell
   .\.venv\Scripts\python.exe src/etl_flow.py --no-load
   ```
   *Ejecuta 4 tareas en memoria:* Extracción desde Staging, Validación de Integridad, Validación de Calidad y Transformación. **No escribe en PostgreSQL 18.**

2. **Modo Carga Completa (`--run-once`):**
   ```powershell
   .\.venv\Scripts\python.exe src/etl_flow.py --run-once
   ```
   *Ejecuta 6 tareas:* Las 4 tareas anteriores más la carga transaccional en `chinook_dw` y la conciliación matemática de cuadratura en PostgreSQL 18.

3. **Modo Servicio Persistente / Despliegue (`--serve` - Opcional):**
   ```powershell
   .\.venv\Scripts\python.exe src/etl_flow.py --serve
   ```
   Registra el deployment local `chinook-local` y mantiene un agente a la espera de ejecuciones programadas. *(Nota: No es requerido para las ejecuciones manuales del proyecto).*

> ⚠️ **Importante:** No ejecute `etl_flow.py` directamente con el botón *Run Python* (Play) del editor; debe invocarse desde la terminal especificando el parámetro `--run-once` o `--no-load`.

---

## 8. Resultados y Cuadratura Matemática Validada

Cada ejecución con carga completa verifica la conciliación aritmética y referencial del Data Warehouse frente a los 15.607 registros de Staging:

```text
======================================================================
CONTROL DE CALIDAD Y CUADRATURA DEL DATA WAREHOUSE
======================================================================
  * dim_date                    :   1.826 filas
  * dim_employee                :       8 filas
  * dim_customer                :      59 filas
  * dim_track                   :   3.503 filas
  * fact_sales                  :   2.240 filas

  * Tracks con playlist_count > 0: 3.503 de 3.503
  * Total acumulado en fact_sales: $2.328,60
  * Inconsistencias matemáticas  : 0
  * Claves foráneas huérfanas    : 0

----------------------------------------------------------------------
CONCILIACIÓN STAGING vs. DATA WAREHOUSE
----------------------------------------------------------------------
  Filas stg_invoice_line : 2.240     | Filas fact_sales : 2.240
  Monto Staging Total    : $2.328,60 | Monto DW Total   : $2.328,60
  Diferencia Aritmética  : $0,00     | Estado           : 100% CONSISTENTE

>>> VALIDACIÓN EXITOSA: El Data Warehouse quedó 100% consistente y cuadrado.
```

---

## 9. Capa de Visualización y Análisis en Microsoft Excel

La visualización y explotación analítica de negocio se presenta mediante **Microsoft Excel**:

### Archivo Principal de Presentación
```powershell
Start-Process ".\excel\Chinook_Analisis_DataWarehouse.xlsx"
```
*(El archivo `docs/historico/Book1.xlsx` se conserva exclusivamente como respaldo histórico original).*

### Arquitectura de Conexión en Excel
- **Motor:** **Power Query** conectado directamente a PostgreSQL 18 (`127.0.0.1:5432`, base de datos `chinook_dw`).
- **Consultas del Modelo Dimensional:** Excel incorpora 5 consultas directas que consumen las tablas del Star Schema:
  1. `dim_date` (1.826 registros)
  2. `dim_customer` (59 registros)
  3. `dim_employee` (8 registros)
  4. `dim_track` (3.503 registros)
  5. `fact_sales` (2.240 registros, $2.328,60)
- **Actualización en Tiempo Real:** En Excel, pulsar la pestaña **Datos → Actualizar todo** (*Refresh All*). Excel consulta en vivo la base de datos PostgreSQL 18; no requiere volver a ejecutar los scripts de Python para refrescar sus tablas dinámicas y gráficos.
- **Vista Analítica Complementaria (`vw_ventas_excel`):** Definida en [`sql/vista_excel.sql`](sql/vista_excel.sql), ofrece una alternativa desnormalizada y aplanada para consultas ad-hoc directas.
