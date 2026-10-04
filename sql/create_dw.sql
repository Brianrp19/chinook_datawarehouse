-- =====================================================================
-- CHINOOK DATA WAREHOUSE - MODELO DIMENSIONAL EN ESTRELLA (STAR SCHEMA)
-- Base de Datos: chinook_dw
-- Motor: PostgreSQL 18
--
-- DECISIONES DE DISEÑO Y MODELADO:
-- 1. Proceso de Negocio: Análisis de Ventas de Música Digital.
-- 2. Grano: Una fila por cada línea de detalle de factura (InvoiceLine).
-- 3. Justificación del Grano: Garantiza la máxima granularidad analítica
--    sin duplicar importes al sumar totales por pista, cliente o tiempo.
-- 4. Estrategia dimensional prevista: SCD Tipo 1.
--    Los cambios de atributos se sobrescriben sin conservar versiones históricas.
-- 5. Rol del Empleado en fact_sales: Representa al agente de soporte
--    actualmente asignado al cliente según Customer.SupportRepId
--    (enfoque SCD Tipo 1, dado que la fuente no almacena histórico de reasignaciones).
-- 6. Claves: Claves sustitutas (Surrogate Keys) controladas y asignadas
--    directamente por el pipeline ETL de Python (INT/BIGINT PRIMARY KEY).
-- 7. Alcance de fuentes: 10 de los 11 CSVs están directamente integrados
--    en el modelo estrella. Playlist.csv fue evaluado en profiling y
--    descartado del DW por no aportar al análisis transaccional de ventas.
-- =====================================================================

-- NOTA: DROP ... CASCADE está previsto para entornos de desarrollo/reconstrucción.
DROP TABLE IF EXISTS fact_sales CASCADE;
DROP TABLE IF EXISTS dim_customer CASCADE;
DROP TABLE IF EXISTS dim_track CASCADE;
DROP TABLE IF EXISTS dim_employee CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;

-- =====================================================================
-- 1. DIMENSION FECHA (dim_date)
-- Cobertura: Calendario completo continuo 2009-01-01 a 2013-12-31
-- =====================================================================
CREATE TABLE dim_date (
    date_key INT PRIMARY KEY,               -- Formato YYYYMMDD (ej. 20090101)
    full_date DATE NOT NULL UNIQUE,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    day INT NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    day_of_week INT NOT NULL,              -- 1 = Lunes, 7 = Domingo
    is_weekend BOOLEAN NOT NULL
);

-- =====================================================================
-- 2. DIMENSION EMPLEADO (dim_employee)
-- =====================================================================
CREATE TABLE dim_employee (
    employee_key INT PRIMARY KEY,           -- Clave sustituta asignada por ETL
    employee_id INT NOT NULL UNIQUE,        -- Clave natural origen (NK)
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    title VARCHAR(60),
    reports_to INT,
    reports_to_name VARCHAR(100),
    birth_date DATE,
    hire_date DATE,
    address VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    postal_code VARCHAR(20),
    phone VARCHAR(30),
    email VARCHAR(100)
);

-- =====================================================================
-- 3. DIMENSION CLIENTE (dim_customer)
-- =====================================================================
CREATE TABLE dim_customer (
    customer_key INT PRIMARY KEY,           -- Clave sustituta asignada por ETL
    customer_id INT NOT NULL UNIQUE,        -- Clave natural origen (NK)
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    company VARCHAR(80),
    address VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    postal_code VARCHAR(20),
    phone VARCHAR(30),
    email VARCHAR(100),
    support_rep_id INT                                        -- FK operacional a Employee
);

-- =====================================================================
-- 4. DIMENSION TRACK / CANCION (dim_track)
-- Desnormaliza: Track + Album + Artist + Genre + MediaType
-- =====================================================================
CREATE TABLE dim_track (
    track_key INT PRIMARY KEY,              -- Clave sustituta asignada por ETL
    track_id INT NOT NULL UNIQUE,           -- Clave natural origen (NK)
    track_name VARCHAR(200) NOT NULL,
    album_id INT,
    album_title VARCHAR(160),
    artist_id INT,
    artist_name VARCHAR(120),
    media_type_id INT,
    media_type_name VARCHAR(120),
    genre_id INT,
    genre_name VARCHAR(120),
    composer VARCHAR(220),
    milliseconds INT NOT NULL CHECK (milliseconds > 0),
    duration_seconds NUMERIC(10, 2) NOT NULL CHECK (duration_seconds > 0),
    duration_minutes NUMERIC(10, 2) NOT NULL CHECK (duration_minutes > 0),
    bytes BIGINT NOT NULL CHECK (bytes > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price > 0),
    playlist_count INT NOT NULL DEFAULT 0 CHECK (playlist_count >= 0)
);

-- =====================================================================
-- 5. TABLA DE HECHOS: VENTAS (fact_sales)
-- =====================================================================
CREATE TABLE fact_sales (
    sales_key BIGINT PRIMARY KEY,           -- Clave sustituta asignada por ETL
    date_key INT NOT NULL REFERENCES dim_date(date_key),
    customer_key INT NOT NULL REFERENCES dim_customer(customer_key),
    track_key INT NOT NULL REFERENCES dim_track(track_key),
    employee_key INT NOT NULL REFERENCES dim_employee(employee_key),
    
    -- Dimensiones degeneradas (claves operativas del negocio)
    invoice_id INT NOT NULL,
    invoice_line_id INT NOT NULL UNIQUE,                       -- Protege el grano y evita duplicados
    
    -- Métricas / Medidas del negocio
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price > 0),
    quantity INT NOT NULL CHECK (quantity > 0),
    total_amount NUMERIC(10, 2) NOT NULL,
    
    -- Restricción de consistencia matemática exacta
    CONSTRAINT chk_total_consistency CHECK (total_amount = unit_price * quantity)
);

-- =====================================================================
-- INDICES PARA OPTIMIZAR CONSULTAS OLAP EN EL DATA WAREHOUSE
-- =====================================================================
CREATE INDEX idx_fact_sales_date ON fact_sales(date_key);
CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_key);
CREATE INDEX idx_fact_sales_track ON fact_sales(track_key);
CREATE INDEX idx_fact_sales_employee ON fact_sales(employee_key);
CREATE INDEX idx_fact_sales_invoice ON fact_sales(invoice_id);
