/*
### 1. Cubo de ventas con todas las combinaciones de dimensiones

Sirve para: obtener ventas por año, país, género, formato y agente, junto con todos sus subtotales y el total general.

CUBE sobre cinco atributos produce 32 combinaciones de agrupación. Es una operación típica de análisis multidimensional.

Cómo interpretarla: un NULL puede representar un subtotal. nivel_agrupacion = 0 indica el detalle completo y 31 el total general.
No sumes todas las filas: los subtotales cuentan las mismas ventas en distintos niveles.
*/

SELECT
    d.year AS anio,
    c.country AS pais,
    t.genre_name AS genero,
    t.media_type_name AS formato,
    e.full_name AS agente,
    GROUPING(
        d.year,
        c.country,
        t.genre_name,
        t.media_type_name,
        e.full_name
    ) AS nivel_agrupacion,
    COUNT(*) AS lineas,
    COUNT(DISTINCT f.invoice_id) AS facturas,
    COUNT(DISTINCT f.customer_key) AS clientes,
    SUM(f.quantity) AS unidades,
    SUM(f.total_amount) AS ventas,
    ROUND(
        SUM(f.total_amount)
        / NULLIF(COUNT(DISTINCT f.invoice_id), 0),
        2
    ) AS promedio_por_factura
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.date_key
JOIN dim_customer c ON c.customer_key = f.customer_key
JOIN dim_track t ON t.track_key = f.track_key
JOIN dim_employee e ON e.employee_key = f.employee_key
GROUP BY CUBE (
    d.year,
    c.country,
    t.genre_name,
    t.media_type_name,
    e.full_name
)
ORDER BY nivel_agrupacion, ventas DESC;



/*
### 2. Similitud de gustos entre todos los clientes

Sirve para: encontrar parejas de clientes que compraron canciones similares. Puede ayudar a identificar públicos para recomendaciones.

Compara cada cliente con todos los demás y calcula el índice de Jaccard:

Canciones compartidas / Canciones distintas entre ambos

Cómo interpretarla: cuanto más cerca de 1, mayor coincidencia. 0 indica que no comparten canciones compradas.
*/


WITH compras AS (
    SELECT DISTINCT customer_key, track_key
    FROM fact_sales
),
totales AS (
    SELECT customer_key, COUNT(*) AS canciones
    FROM compras
    GROUP BY customer_key
),
compartidas AS (
    SELECT
        a.customer_key AS cliente_a,
        b.customer_key AS cliente_b,
        COUNT(*) AS canciones_compartidas
    FROM compras a
    JOIN compras b
        ON b.track_key = a.track_key
       AND a.customer_key < b.customer_key
    GROUP BY a.customer_key, b.customer_key
),
similitud AS (
    SELECT
        a.customer_key AS cliente_a,
        b.customer_key AS cliente_b,
        COALESCE(c.canciones_compartidas, 0)
            AS canciones_compartidas,
        a.canciones + b.canciones
            - COALESCE(c.canciones_compartidas, 0)
            AS canciones_union,
        ROUND(
            COALESCE(c.canciones_compartidas, 0)::numeric
            / NULLIF(
                a.canciones + b.canciones
                - COALESCE(c.canciones_compartidas, 0),
                0
            ),
            4
        ) AS indice_jaccard
    FROM totales a
    CROSS JOIN totales b
    LEFT JOIN compartidas c
        ON c.cliente_a = a.customer_key
       AND c.cliente_b = b.customer_key
    WHERE a.customer_key < b.customer_key
)
SELECT
    ca.full_name AS cliente_a,
    cb.full_name AS cliente_b,
    s.canciones_compartidas,
    s.canciones_union,
    s.indice_jaccard
FROM similitud s
JOIN dim_customer ca ON ca.customer_key = s.cliente_a
JOIN dim_customer cb ON cb.customer_key = s.cliente_b
ORDER BY s.indice_jaccard DESC, s.canciones_compartidas DESC;


/*
3. Ventas diarias con ventanas móviles y detección de picos

Sirve para: detectar días con ventas inusualmente altas respecto a los 30 días anteriores, por país.

Construye todas las combinaciones de fecha y país, incluso cuando no hubo ventas. Después calcula promedio, desviación estándar, acumulado y puntuación estadística.

Cómo interpretarla: una puntuación de 3 significa que la venta está tres desviaciones por encima del promedio previo. Es una señal para investigar;
no demuestra un error, especialmente con ventas tan esporádicas como Chinook.
*/


WITH paises AS (
    SELECT DISTINCT country
    FROM dim_customer
),
ventas_diarias AS (
    SELECT
        d.full_date AS fecha,
        c.country AS pais,
        SUM(f.total_amount) AS ventas
    FROM fact_sales f
    JOIN dim_date d ON d.date_key = f.date_key
    JOIN dim_customer c ON c.customer_key = f.customer_key
    GROUP BY d.full_date, c.country
),
serie AS (
    SELECT
        d.full_date AS fecha,
        p.country AS pais,
        COALESCE(v.ventas, 0) AS ventas
    FROM dim_date d
    CROSS JOIN paises p
    LEFT JOIN ventas_diarias v
        ON v.fecha = d.full_date
       AND v.pais IS NOT DISTINCT FROM p.country
),
estadisticas AS (
    SELECT
        *,
        COUNT(*) OVER historial AS dias_previos,
        AVG(ventas) OVER historial AS promedio_previo,
        STDDEV_SAMP(ventas) OVER historial AS desviacion_previa,
        SUM(ventas) OVER (
            PARTITION BY pais, EXTRACT(YEAR FROM fecha)
            ORDER BY fecha
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS acumulado_anual
    FROM serie
    WINDOW historial AS (
        PARTITION BY pais
        ORDER BY fecha
        ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
    )
),
evaluacion AS (
    SELECT
        *,
        (ventas - promedio_previo)
            / NULLIF(desviacion_previa, 0) AS puntuacion_z
    FROM estadisticas
)
SELECT
    fecha,
    pais,
    ventas,
    ROUND(promedio_previo, 2) AS promedio_30_dias,
    ROUND(desviacion_previa, 2) AS desviacion_30_dias,
    ROUND(puntuacion_z, 2) AS puntuacion_z,
    acumulado_anual
FROM evaluacion
WHERE dias_previos = 30
  AND puntuacion_z >= 3
ORDER BY puntuacion_z DESC, ventas DESC;


/*
### 4. Prueba de carga con 2.240.000 filas virtuales

Esta es la que más sirve para exigirle recursos con tu tamaño actual.

Sirve para: observar el costo de procesar millones de filas, agrupar, contar facturas distintas y ordenar resultados. Multiplica virtualmente las ventas por 1.000; no inserta registros.

Cada repetición se interpreta como un escenario independiente.

Empieza cambiando 1000 por 100 y después sube a 1000:

| Repeticiones | Filas virtuales |
|---|---:|
| 100 | 224.000 |
| 1.000 | 2.240.000 |
| 5.000 | 11.200.000 |

Esta es una prueba sintética: exige procesamiento, pero no reproduce exactamente una tabla real de millones de ventas con sus índices y distribución de datos.

En el plan de ejecución revisa:

- Execution Time: duración total en PostgreSQL.
- Sort Method: si ordenó en memoria o usó disco.
- temp read / written: uso de archivos temporales.
- actual rows y loops: cuántas filas procesó cada operación.

Si compartes el resultado del EXPLAIN de la cuarta consulta, podemos identificar qué parte consumió más recursos.
*/


EXPLAIN (ANALYZE, BUFFERS)
WITH ventas_simuladas AS MATERIALIZED (
    SELECT
        g.escenario,
        f.invoice_id,
        f.customer_key,
        f.track_key,
        f.date_key,
        f.quantity,
        f.total_amount
    FROM fact_sales f
    CROSS JOIN generate_series(1, 1000) AS g(escenario)
),
resumen AS (
    SELECT
        s.escenario,
        d.year AS anio,
        c.country AS pais,
        t.genre_name AS genero,
        SUM(s.total_amount) AS ventas,
        SUM(s.quantity) AS unidades,
        COUNT(DISTINCT s.invoice_id) AS facturas,
        COUNT(DISTINCT s.customer_key) AS clientes
    FROM ventas_simuladas s
    JOIN dim_date d ON d.date_key = s.date_key
    JOIN dim_customer c ON c.customer_key = s.customer_key
    JOIN dim_track t ON t.track_key = s.track_key
    GROUP BY
        s.escenario,
        d.year,
        c.country,
        t.genre_name
)
SELECT
    *,
    DENSE_RANK() OVER (
        PARTITION BY escenario, anio, pais
        ORDER BY ventas DESC
    ) AS ranking_genero,
    ROUND(
        100.0 * ventas
        / NULLIF(
            SUM(ventas) OVER (
                PARTITION BY escenario, anio, pais
            ),
            0
        ),
        2
    ) AS participacion
FROM resumen
ORDER BY escenario, anio, pais, ranking_genero;
