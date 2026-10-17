-- =====================================================================
-- CHINOOK DATA WAREHOUSE - VISTA ANALÍTICA PARA EXCEL / POWER BI
-- Archivo: sql/vista_excel.sql
-- Base de Datos: chinook_dw
--
-- PROPÓSITO:
-- Facilita la conexión con herramientas analíticas (Excel, Power BI, Tableau).
-- Esta vista desnormaliza en tiempo de consulta la tabla de hechos con
-- las cuatro dimensiones, mostrando nombres legibles en lugar de códigos
-- de claves sustitutas.
-- =====================================================================

DROP VIEW IF EXISTS vw_ventas_excel;

CREATE OR REPLACE VIEW vw_ventas_excel AS
SELECT 
    f.sales_key,
    f.invoice_id,
    f.invoice_line_id,
    
    -- Atributos de Fecha (dim_date)
    d.full_date AS fecha,
    d.year AS anio,
    d.quarter AS trimestre,
    d.month AS mes_numero,
    d.month_name AS mes,
    d.day AS dia,
    d.day_name AS dia_semana,
    d.is_weekend AS es_fin_semana,
    
    -- Atributos de Cliente (dim_customer)
    c.full_name AS cliente,
    c.company AS empresa_cliente,
    c.country AS pais_cliente,
    c.state AS estado_cliente,
    c.city AS ciudad_cliente,
    
    -- Atributos de Empleado / Agente (dim_employee)
    e.full_name AS agente_soporte,
    e.title AS cargo_agente,
    e.reports_to_name AS supervisor_agente,
    
    -- Atributos de Canción y Música (dim_track)
    t.track_name AS cancion,
    t.artist_name AS artista,
    t.album_title AS album,
    t.genre_name AS genero,
    t.media_type_name AS formato,
    t.duration_minutes AS duracion_minutos,
    t.playlist_count AS cantidad_playlists,
    
    -- Medidas Numéricas del Negocio (fact_sales)
    f.unit_price AS precio_unitario,
    f.quantity AS cantidad,
    f.total_amount AS monto_total
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
JOIN dim_customer c ON f.customer_key = c.customer_key
JOIN dim_employee e ON f.employee_key = e.employee_key
JOIN dim_track t ON f.track_key = t.track_key;

-- Comentario descriptivo en el catálogo de PostgreSQL
COMMENT ON VIEW vw_ventas_excel IS 'Vista consolidada de ventas y dimensiones para análisis en Excel y reportes de BI';
