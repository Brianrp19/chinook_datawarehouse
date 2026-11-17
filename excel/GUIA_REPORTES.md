# Reporte de Chinook: resumen y tablas dinámicas

El archivo de entrega es [Chinook_Reporte_Ejecutivo.xlsx](Chinook_Reporte_Ejecutivo.xlsx). Contiene **seis hojas visibles: un resumen y cinco tablas dinámicas nativas**. Las tablas utilizan el Modelo de datos y las cinco consultas PostgreSQL del libro.

## Qué pide el proyecto

La página 3 del enunciado pide «Visualizar los resultados mediante tablas dinámicas en Excel conectadas al DW». La rúbrica de la página 7 asigna el 10 % a «Implementación DW y Visualización»: se debe demostrar la conexión y responder con claridad a las necesidades del negocio. El documento no fija un número de tablas.

El resumen permite presentar el panorama general. Las tablas visibles permiten explicar y explorar de dónde salen los resultados.

## Estructura del archivo

| Hoja | Qué muestra | Pregunta que responde |
|---|---|---|
| `00_Resumen` | Tres gráficos, filtros y botones hacia las tablas | ¿Cuál es el panorama de ventas en la selección actual? |
| `01_Ventas` | Tabla dinámica por año: ingresos, facturas, unidades, clientes y promedio por factura | ¿Cómo evolucionan las ventas? |
| `02_Paises` | Tabla dinámica de ventas por país | ¿Qué mercados generan más ingresos? |
| `03_Clientes` | Tabla dinámica de compras por cliente | ¿Qué clientes compran más? |
| `04_Catalogo` | Tabla dinámica por género, con ingresos, unidades, facturas y pistas distintas | ¿Qué géneros tienen mayor demanda? |
| `05_Formatos` | Tabla dinámica por formato de audio o video | ¿Cómo se distribuyen las ventas entre formatos? |

Las cinco tablas empiezan en `B9`. Al seleccionar una se puede abrir **Analizar tabla dinámica → Lista de campos** para reorganizar filas, columnas o valores. En cada análisis, el botón **RESUMEN** regresa a la primera hoja. Las hojas no están protegidas.

Los filtros por año, país y género comparten su selección entre el resumen y las cinco tablas de negocio.

El gráfico anual muestra los años seleccionados. Los gráficos de países y géneros muestran **hasta cinco categorías con mayores ingresos**; sus rangos se adaptan a la selección. Las tablas correspondientes muestran todas las categorías con ventas, sin un límite Top 5 o Top 10. Los totales generales de las tablas representan la selección completa; no tienen por qué coincidir con la suma de los cinco elementos de un gráfico.

## Por qué las ventas anuales son pequeñas

Chinook es una base de demostración. Su autor explica que la información de ventas se genera aleatoriamente; no corresponde a la facturación real de una tienda. Ver la [documentación original](https://github.com/lerocha/chinook-database#sample-data).

En los CSV del proyecto, 2010 contiene 83 facturas y 455 unidades: 424 a precio 0,99 y 31 a precio 1,99. El cálculo es `424 × 0,99 + 31 × 1,99 = 481,45`. El reporte conserva esos importes; la cifra baja proviene del tamaño y los precios del conjunto de ejemplo.

## Qué calculan las tablas

La granularidad de `fact_sales` es una fila por detalle de factura. Una factura puede tener varias líneas; contar sus filas no equivale a contar facturas.

| Medida | Cálculo | Referencia del conjunto original sin filtros |
|---|---|---:|
| Ingresos | Suma de `total_amount` | 2.328,60 |
| Facturas | Conteo distinto de `invoice_id` | 412 |
| Unidades | Suma de `quantity` | 2.240 |
| Clientes | Conteo distinto de `customer_key` en las ventas seleccionadas | 59 |
| Promedio por factura | Ingresos / facturas diferentes de la selección | 5,65 |

Los gráficos toman sus datos de `01_Ventas`, `02_Paises` y `04_Catalogo` mediante rangos que cambian con el tamaño de las tablas. Las cinco tablas que sustentan el reporte están visibles.

Los totales generales de conteos distintos y promedios los calcula el modelo sobre toda la selección; no deben obtenerse sumando las filas. Una factura puede contener diferentes géneros.

Los importes son ingresos por ventas en la moneda de la fuente. No hay datos de costos para calcular ganancias o rentabilidad. Al filtrar un género, el promedio por factura utiliza las líneas seleccionadas y las facturas que las contienen, no necesariamente el importe completo de cada factura.

## Conexión y actualización

```text
CSV → ETL Staging → chinook_staging → ETL del DW → chinook_dw
                                                        ↓
                                          Cinco consultas Power Query
                                                        ↓
                                          Modelo de datos relacionado
                                                        ↓
                                          Cinco tablas dinámicas visibles
                                                        ↓
                                          Resumen: gráficos y filtros
```

El origen conservado es **`localhost:5432`**, base **`chinook_dw`**. `localhost` significa el equipo donde se abre Excel. El libro no toma automáticamente los valores de `.env`.

| Consulta | Función | Filas de la copia original |
|---|---|---:|
| `public dim_date` | Calendario | 1.826 |
| `public dim_customer` | Clientes y países | 59 |
| `public dim_employee` | Asesores de soporte | 8 |
| `public dim_track` | Catálogo, géneros y formatos | 3.503 |
| `public fact_sales` | Detalles e importes de venta | 2.240 |

La tabla de hechos se relaciona con las cuatro dimensiones mediante sus claves. Las consultas leen las cinco tablas directamente; el libro no necesita la vista alternativa `vw_ventas_excel`.

Usar Excel de escritorio para Windows con Power Query y Modelo de datos disponibles. La configuración detallada está en la [sección 9 del README](../README.md#9-capa-de-visualización-y-análisis-en-microsoft-excel).

1. Tener PostgreSQL funcionando y el DW preparado y cargado mediante su ETL. Abrir Excel no crea la base ni ejecuta Prefect.
2. Confirmar el servidor, puerto, nombre de base y usuario con conexión y lectura de las cinco tablas. El lector de Staging no obtiene acceso al DW automáticamente.
3. Abrir **Datos → Consultas y conexiones**. Si el DW usa otro servidor o puerto, editar el paso `Source`/`Origen` de las cinco consultas. El origen debe indicar `PostgreSQL.Database("servidor:puerto", "chinook_dw")` con los valores reales.
4. Introducir las credenciales cuando Excel las solicite. Para cambiar una cuenta guardada, revisar **Datos → Obtener datos → Configuración de origen de datos → Editar permisos**.
5. Ejecutar **Datos → Actualizar todo** y esperar a que finalicen las cinco consultas sin errores. Si hace falta, actualizar después las tablas dinámicas desde **Analizar tabla dinámica → Actualizar**.
6. Borrar los filtros, contrastar el total general de `01_Ventas` con el DW y guardar.

El libro conserva datos importados y permite explorarlos sin PostgreSQL disponible. Ver cifras o cambiar filtros demuestra el análisis de esa copia, no una conexión actual. **Actualizar todo** toma una nueva lectura del DW; no es actualización continua ni ejecuta el ETL. Un error de conexión puede dejar visibles los datos anteriores.

## Demostración breve para la exposición

1. Empezar en `00_Resumen`: explicar la evolución anual y los países y géneros con más ingresos.
2. Seleccionar **2009**: el gráfico anual debe mostrar ingresos de **449,46** con el conjunto original.
3. Pulsar **VENTAS**: el total de la tabla debe mostrar esos **449,46** y **83** facturas. Seleccionar la tabla y mostrar su lista de campos.
4. Volver al resumen, borrar año y seleccionar **USA**: ingresos **523,06**. Mostrar la tabla de países.
5. Borrar país y seleccionar **Rock**: ingresos **826,65**. Mostrar la tabla del catálogo.
6. Borrar los filtros y recuperar en `01_Ventas` los totales de **2.328,60**, **412** facturas y **2.240** unidades.
7. Con el DW disponible, demostrar una actualización correcta y contrastar el resultado con PostgreSQL.

Las cifras de referencia pertenecen al conjunto original. Si se incorporan nuevas ventas legítimas, pueden cambiar; corresponde conciliarlas con el DW.


Se verificaron las tablas, los gráficos y los filtros con los datos guardados, incluyendo guardar y reabrir el libro. **El refresco contra un DW activo debe comprobarse en el equipo de la presentación.**
