# Chinook Data Warehouse & ETL Pipeline

Este repositorio contiene la arquitectura, el diseño dimensional y el pipeline ETL completo (Extracción, Perfilado, Transformación, Carga y Orquestación con Prefect) para el análisis de ventas de música digital basado en el conjunto de datos de **Chinook**.

---

## 1. Arquitectura y Modelo Dimensional (Star Schema)

* **Proceso de Negocio:** Análisis de ventas de pistas musicales y facturación a clientes.
* **Grano:** Una fila por cada línea de detalle de factura (`InvoiceLine`).
* **Estrategia Dimensional:** SCD Tipo 1 (Slowly Changing Dimensions Tipo 1).
* **Restricción de Consistencia:** `total_amount = unit_price * quantity`.

### Diagrama del Modelo Estrella

```text
                      ┌──────────────┐
                      │   dim_date   │
                      │  (1,826 d.)  │
                      └──────┬───────┘
                             │
     ┌──────────────┐        │        ┌──────────────┐
     │ dim_customer │───┐    │    ┌───│  dim_track   │
     │  (59 reg.)   │   │    │    │   │ (3,503 reg.) │
     └──────────────┘   ▼    ▼    ▼   └──────────────┘
                    ┌──────────────────┐
                    │    fact_sales    │
                    │   (2,240 reg.)   │
                    │    $2,328.60     │
                    └──────────────────┘
                             ▲
                             │
                      ┌──────┴───────┐
                      │ dim_employee │
                      │   (8 reg.)   │
                      └──────────────┘
```

* **`fact_sales` (Tabla de Hechos):** Almacena las transacciones a nivel de detalle. Claves foráneas a las 4 dimensiones, claves degeneradas (`invoice_id`, `invoice_line_id`) y métricas (`unit_price`, `quantity`, `total_amount`).
* **`dim_date`:** Calendario continuo de 5 años (2009-01-01 a 2013-12-31) con año, trimestre, mes, día, día de semana y marca de fin de semana.
* **`dim_customer`:** Datos demográficos del cliente y país de residencia.
* **`dim_employee`:** Empleados y soporte técnico con resolución jerárquica de supervisor (`reports_to_name`).
* **`dim_track`:** Desnormalización de pistas musicales integrando `Track`, `Album`, `Artist`, `Genre`, `MediaType` y el conteo de apariciones en listas (`playlist_count` desde `PlaylistTrack`).

---

## 2. Estructura del Proyecto

```text
chinook_datawarehouse/
│
├── data/
│   └── raw/                          # 11 Archivos CSV originales de Chinook
│       ├── Album.csv
│       ├── Artist.csv
│       ├── Customer.csv
│       ├── Employee.csv
│       ├── Genre.csv
│       ├── Invoice.csv
│       ├── InvoiceLine.csv
│       ├── MediaType.csv
│       ├── Playlist.csv
│       ├── PlaylistTrack.csv
│       └── Track.csv
│
├── sql/
│   └── create_dw.sql                 # DDL de PostgreSQL: tablas, PKs, FKs, CHECKs e índices
│
├── src/
│   ├── explorar_datos.py             # Profiling inicial: dimensiones, nulos y duplicados
│   ├── validar_integridad.py         # Validación de integridad referencial (cero huérfanos)
│   ├── validar_calidad_negocio.py    # Reglas de negocio: precios, cantidades y montos
│   ├── validar_modelo_dw.py          # Chequeos previos: límites VARCHAR y campos numéricos
│   ├── transform.py                  # Transformación dimensional (T) de los CSV a DataFrames
│   ├── load.py                       # Carga a PostgreSQL (L) y conciliación matemática
│   └── etl_flow.py                   # Orquestador del flujo ETL con Prefect
│
├── .gitignore
├── requirements.txt                  # Dependencias congeladas del entorno virtual
└── README.md
```

---

## 3. Guía de Instalación y Replicación (Para el Equipo)

Sigue estos pasos para levantar el Data Warehouse en tu máquina local:

### Paso 1: Prerrequisitos
* **Python 3.11+** (recomendado 3.14 o 3.12).
* **PostgreSQL 16+** instalado y corriendo en el puerto por defecto (`5432`).
* **pgAdmin** instalado.
* **Git** instalado.

### Paso 2: Clonar el Repositorio
```bash
git clone <URL_DEL_REPOSITORIO>
cd chinook_datawarehouse
```

### Paso 3: Crear y Activar el Entorno Virtual
En Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Paso 4: Instalar Dependencias
```powershell
python -m pip install -r requirements.txt
```

### Paso 5: Crear la Base de Datos en pgAdmin
1. Abre **pgAdmin** y conéctate a tu servidor local de PostgreSQL.
2. Haz clic derecho sobre **Databases** > **Create** > **Database...**
3. Nómbrala: `chinook_dw`
4. Guarda los cambios.

### Paso 6: Crear el Esquema Físico (Tablas)
1. En pgAdmin, haz clic derecho sobre `chinook_dw` > **Query Tool**.
2. Abre o pega el contenido del archivo `sql/create_dw.sql`.
3. Ejecuta la consulta (`F5`). Debe confirmar la creación de las 5 tablas y sus índices.

### Paso 7: Configurar Credenciales y Ejecutar el ETL
En tu terminal de PowerShell con `(.venv)` activo:
```powershell
$env:PGPASSWORD="TU_CONTRASEÑA_DE_POSTGRESQL"
python src/etl_flow.py
```

---

## 4. Resultados y Conciliación Esperada

Al ejecutar `python src/etl_flow.py`, **Prefect** debe marcar todas las tareas en estado `Completed()` y mostrar la siguiente cuadratura en consola:

```text
======================================================================
CONTROL DE CALIDAD Y CUADRATURA DEL DATA WAREHOUSE
======================================================================
  * dim_date       :   1826 filas
  * dim_employee   :      8 filas
  * dim_customer   :     59 filas
  * dim_track      :   3503 filas
  * fact_sales     :   2240 filas

  * Tracks con playlist_count > 0: 3503 de 3503
  * Total acumulado en fact_sales : $2,328.60 (Esperado: $2,328.60)
  * Inconsistencias matemáticas   : 0

----------------------------------------------------------------------
CONCILIACION FUENTE ORIGINAL vs. DATA WAREHOUSE
----------------------------------------------------------------------
  Filas InvoiceLine.csv : 2240     | Filas fact_sales : 2240
  Monto Fuente Total    : $2328.60 | Monto DW Total   : $2328.60
  Errores Aritméticos   : 0        | Errores en DW    : 0

>>> VALIDACION EXITOSA: El Data Warehouse quedó 100% consistente y cuadrado.
```
