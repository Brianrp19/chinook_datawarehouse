# 📋 Plan DEFINITIVO — Reorganización en 2 Repos

## Arquitectura objetivo

```
              REPO 1                              REPO 2
       chinook_staging_etl                 chinook_datawarehouse

  11 CSV                              chinook_staging (extracción)
     ↓                                        ↓
  Prefect                                  Prefect
     ├── Extraer CSV                        ├── Extraer staging
     ├── Cargar staging (Full Refresh)      ├── Transformar
     └── Validar staging                    ├── Cargar DW
             ↓                              └── Validar DW
     chinook_staging                            ↓
     11 tablas stg_*                       chinook_dw
                                           ├── dim_date
                                           ├── dim_customer
                                           ├── dim_employee
                                           ├── dim_track
                                           └── fact_sales
                                                ↓
                                              Excel
```

---

## Repo 1: `chinook_staging_etl` (Miguel + compañero)

### Propósito
Cargar los 11 CSVs tal cual están en tablas staging de PostgreSQL.
**Sin limpieza ni transformación** — copia fiel del origen, solo tipos mínimos para cargar.

### Base de datos: `chinook_staging`

### Las 11 tablas (nombres acordados)

| Tabla | CSV origen | Filas esperadas |
|---|---|---|
| `stg_album` | Album.csv | 347 |
| `stg_artist` | Artist.csv | 275 |
| `stg_customer` | Customer.csv | 59 |
| `stg_employee` | Employee.csv | 8 |
| `stg_genre` | Genre.csv | 25 |
| `stg_invoice` | Invoice.csv | 412 |
| `stg_invoice_line` | InvoiceLine.csv | 2240 |
| `stg_media_type` | MediaType.csv | 5 |
| `stg_playlist` | Playlist.csv | 18 |
| `stg_playlist_track` | PlaylistTrack.csv | 8715 |
| `stg_track` | Track.csv | 3503 |

---

### ⚠️ CRÍTICO: Nombres de columnas en PostgreSQL

Los CSVs tienen columnas CamelCase (`CustomerId`, `FirstName`, `TrackId`).
Nuestro `transform.py` espera exactamente esos nombres.

PostgreSQL convierte todo a minúsculas si no se usan comillas.

**Miguel DEBE usar comillas dobles en el DDL para preservar los nombres originales:**

```sql
-- ✅ CORRECTO
CREATE TABLE stg_customer (
    "CustomerId" INTEGER,
    "FirstName" VARCHAR(100),
    "LastName" VARCHAR(100),
    "Company" VARCHAR(100),
    ...
);

-- ❌ INCORRECTO (PostgreSQL guardará customerid, firstname...)
CREATE TABLE stg_customer (
    CustomerId INTEGER,
    FirstName VARCHAR(100)
);
```

Así se preserva la cadena:
```
CSV "CustomerId" → STAGING "CustomerId" → Repo 2 df["CustomerId"]
```
Y nuestro código sigue sirviendo sin cambios.

---

### Flujo Prefect (3 tasks)

```
Task 1: Extraer CSV         → pd.read_csv() de los 11 archivos
Task 2: Cargar staging      → Full Refresh (TRUNCATE + INSERT)
Task 3: Validar staging     → Conteos + MIN/MAX de IDs
```

### Full Refresh: transacción atómica

La recarga debe ser **atómica** (todo o nada):

```python
with engine.begin() as conn:     # Inicia transacción
    # 1. TRUNCATE explícito de las 11 tablas
    conn.execute(text("""
        TRUNCATE TABLE
            stg_album,
            stg_artist,
            stg_customer,
            stg_employee,
            stg_genre,
            stg_invoice,
            stg_invoice_line,
            stg_media_type,
            stg_playlist,
            stg_playlist_track,
            stg_track;
    """))

    # 2. Cargar las 11 tablas
    for tabla, df in data.items():
        df.to_sql(tabla, conn, if_exists="append", index=False)

    # 3. Validar conteos
    validar_staging(conn, data)

    # Si algo falla → ROLLBACK automático
    # Si todo pasa → COMMIT
```

Esto evita que un error a mitad de ejecución deje 5 tablas nuevas y 6 vacías.

### Validación del staging

No solo conteos — también conciliación básica:

```
✅ 11 archivos encontrados
✅ 11 tablas cargadas

Conteos:
  Album.csv          347 = stg_album          347  ✓
  Artist.csv         275 = stg_artist         275  ✓
  Customer.csv        59 = stg_customer        59  ✓
  Employee.csv         8 = stg_employee         8  ✓
  Genre.csv           25 = stg_genre           25  ✓
  Invoice.csv        412 = stg_invoice        412  ✓
  InvoiceLine.csv   2240 = stg_invoice_line  2240  ✓
  MediaType.csv        5 = stg_media_type       5  ✓
  Playlist.csv        18 = stg_playlist        18  ✓
  PlaylistTrack.csv 8715 = stg_playlist_track 8715 ✓
  Track.csv         3503 = stg_track         3503  ✓

Valores de control:
  InvoiceId:  MIN=1   MAX=412
  TrackId:    MIN=1   MAX=3503
  CustomerId: MIN=1   MAX=59
```

### Estructura de archivos

```
chinook_staging_etl/
├── data/
│   └── raw/                  ← Los 11 CSVs
├── sql/
│   └── create_staging.sql    ← CREATE TABLE con comillas en columnas
├── src/
│   ├── extract.py            ← Lee los 11 CSVs con pandas
│   ├── load_staging.py       ← TRUNCATE explícito + to_sql() atómico
│   ├── validate_staging.py   ← Conteos + MIN/MAX
│   └── etl_staging_flow.py   ← Flujo Prefect (3 tasks)
├── .env                      ← ⛔ NUNCA a GitHub
├── .env.example              ← ✅ Va a GitHub (sin contraseñas reales)
├── .gitignore                ← Incluye .env
├── requirements.txt
└── README.md
```

### `.env.example` del Repo 1

```env
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGDATABASE=chinook_staging
PGPASSWORD=TU_PASSWORD
PREFECT_API_URL=http://127.0.0.1:4200/api
```

> ⚠️ Solo `.env.example` va a GitHub. El `.env` con contraseñas reales **jamás** se sube.

---

## Repo 2: `chinook_datawarehouse` (Brian + compañero)

### Propósito
Leer desde staging, transformar al modelo dimensional y cargar el DW.

### Bases de datos
- **`chinook_staging`** → extracción de datos
- **`chinook_dw`** → carga de dimensiones y hechos

> **Nota:** Ambas conexiones usan `postgres` para desarrollo. No es técnicamente "solo lectura",
> pero para este proyecto funciona. En producción se usarían usuarios con permisos limitados.

### El cambio clave en el código

```python
# ANTES (lee CSVs directamente)
def extract_raw_data():
    raw_dir = get_raw_data_dir()
    return {
        "album": pd.read_csv(raw_dir / "Album.csv"),
        "artist": pd.read_csv(raw_dir / "Artist.csv"),
        ...
    }

# DESPUÉS (lee del staging — misma función, misma interfaz)
def extract_raw_data():
    engine_stg = get_staging_engine()
    return {
        "album": pd.read_sql("SELECT * FROM stg_album", engine_stg),
        "artist": pd.read_sql("SELECT * FROM stg_artist", engine_stg),
        ...
    }
```

> **Tip:** Al mantener el mismo nombre `extract_raw_data()` y la misma estructura del diccionario,
> **todo lo demás sigue funcionando sin cambios**:
> - `build_dim_date()`
> - `build_dim_employee()`
> - `build_dim_customer()`
> - `build_dim_track()`
> - `build_fact_sales()`

### `.env.example` del Repo 2

```env
# Conexión a STAGING (extracción)
STG_HOST=localhost
STG_PORT=5432
STG_USER=postgres
STG_DATABASE=chinook_staging
STG_PASSWORD=TU_PASSWORD

# Conexión al DW (carga)
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGDATABASE=chinook_dw
PGPASSWORD=TU_PASSWORD

# Prefect
PREFECT_API_URL=http://127.0.0.1:4201/api
```

### Lo que cambia en cada archivo

| Archivo | Cambio |
|---|---|
| `transform.py` | `extract_raw_data()` → `pd.read_sql()` desde `stg_*` |
| `.env` | Agregar conexión a `chinook_staging` |
| `validar_integridad.py` | Validar contra staging en vez de CSVs |
| `validar_calidad_negocio.py` | Validar contra staging en vez de CSVs |
| `etl_flow.py` | Cambios mínimos |
| `load.py` | **No cambia** |
| `create_dw.sql` | **No cambia** |
| Excel / drivers | **No cambian** |

### `data/raw/` — NO eliminar todavía

> ⚠️ No borrar los CSVs del Repo 2 hasta que:
> 1. Repo 1 funcione y las 11 tablas `stg_*` estén cargadas
> 2. Repo 2 funcione leyendo de staging
> 3. Se compruebe: **2240 filas, $2,328.60, 0 inconsistencias**
>
> Cuando todo esté validado, ahí sí se eliminan.

---

## Orden de trabajo

```
┌──────────────────────────────────────────────────────┐
│  FASE 1: Miguel hace el Repo 1 (staging)             │
│  ─────────────────────────────────────────            │
│  • Crea chinook_staging_etl                          │
│  • Crea base chinook_staging + 11 tablas stg_*       │
│  • ⚠️ USA COMILLAS en nombres de columnas            │
│  • Full Refresh atómico (transacción)                │
│  • Valida conteos + MIN/MAX                          │
│  • Sube a GitHub (solo .env.example, NO .env)        │
│                                                      │
│  Brian espera / puede preparar conexión a staging    │
│  en su .env pero NO modifica código aún              │
└──────────────────────────────────────────────────────┘
                        ↓
        Miguel entrega staging estable:
        stg_album         347
        stg_artist        275
        stg_customer       59
        stg_employee        8
        stg_genre          25
        stg_invoice       412
        stg_invoice_line 2240
        stg_media_type      5
        stg_playlist       18
        stg_playlist_track 8715
        stg_track        3503
                        ↓
┌──────────────────────────────────────────────────────┐
│  FASE 2: Brian adapta el Repo 2 (DW)                │
│  ─────────────────────────────────────────            │
│  • Verifica que chinook_staging tiene datos           │
│  • Modifica extract_raw_data() → pd.read_sql()       │
│  • Ajusta validaciones                               │
│  • Prueba: staging → DW completo                     │
│  • Comprueba: 2240 filas, $2,328.60, 0 errores       │
│  • Si todo cuadra → elimina data/raw/                │
│  • Commit y push                                     │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│  FASE 3: Pregunta pendiente al profesor               │
│  ─────────────────────────────────────────            │
│  "Profe, lo de MS después del DW, ¿qué significa?"   │
│                                                      │
│  → No asumir que es Modelo Semántico hasta confirmar │
│  → Define si necesitan una capa más entre DW y Excel │
└──────────────────────────────────────────────────────┘
```

---

## Resumen

| Pregunta | Respuesta |
|---|---|
| ¿Se pierde trabajo? | No, se reutiliza la mayor parte de la lógica actual del DW |
| ¿Quién hace qué primero? | **Miguel** → Repo 1 (staging) |
| ¿Brian espera? | **Sí**, hasta que staging esté listo con datos |
| ¿Se borran los CSVs del Repo 2? | **Solo después** de validar todo |
| ¿Staging limpia datos? | **No**, copia fiel del CSV |
| ¿La limpieza dónde va? | **Repo 2** (transform.py) |
| ¿Comillas en columnas? | **Sí**, obligatorio para preservar CamelCase |
| ¿Contraseñas a GitHub? | **Jamás**, solo `.env.example` |
| ¿Qué es MS? | **Pendiente** de confirmar con el profesor |
