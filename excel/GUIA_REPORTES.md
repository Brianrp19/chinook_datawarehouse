# Reportes de Chinook en Excel

El objetivo es convertir los datos del Data Warehouse en respuestas comprensibles sobre las ventas. El Excel es la capa de análisis y presentación: consulta el DW, relaciona sus tablas y permite agrupar, filtrar y comparar resultados. No carga los CSV al Staging ni ejecuta el ETL del DW.

## Archivos de la entrega

- [Chinook_Reporte_Ejecutivo.xlsx](Chinook_Reporte_Ejecutivo.xlsx): libro principal, con tablas dinámicas nativas, gráficos e indicadores que responden a los filtros.
- [Chinook_Analisis_DataWarehouse.xlsx](Chinook_Analisis_DataWarehouse.xlsx): archivo anterior, conservado sin modificaciones.

Se entrega **un libro con varias hojas**, para compartir el modelo y los filtros. El enunciado no establece una cantidad de archivos Excel.

## Qué pide el proyecto y cómo se cubre

El enunciado de «Proyecto # 1 Minería de Datos» pide visualizar los resultados mediante tablas dinámicas de Excel conectadas al DW. En la rúbrica, «Implementación DW y Visualización» tiene un peso del **10 %**. Para la mejor valoración, la conexión debe funcionar y los reportes deben responder con claridad a las necesidades del usuario. Los informes genéricos, los errores de conexión, los duplicados y las sumas incorrectas perjudican la evaluación.

| Criterio | Cómo se atiende | Cómo comprobarlo |
|---|---|---|
| Consumir el DW | Cinco consultas Power Query a las cuatro dimensiones y `fact_sales` | Revisar Datos → Consultas y conexiones y demostrar un refresco con PostgreSQL disponible |
| Usar tablas dinámicas reales | Doce tablas dinámicas basadas en el Modelo de datos | Abrir `06_Explorar`, hacer clic en la tabla y mostrar su lista de campos |
| Responder preguntas del negocio | Tres reportes sobre evolución, clientes y catálogo | Explicar qué pregunta responde cada gráfico y qué decisión podría orientar |
| Sumar y contar correctamente | Medidas explícitas para importes, cantidades e identificadores diferentes | Contrastar los indicadores con los totales esperados y con el DW |
| Permitir explorar | Filtros compartidos por año, país del cliente y género | Seleccionar un año y observar el cambio en los tres reportes |
| Presentar con claridad | Indicadores, títulos, rankings, unidades y notas de interpretación | Distinguir ingresos de ganancias, títulos de pistas e indicadores totales de rankings |

**Estado de esta entrega:** se conserva el modelo y las conexiones del archivo anterior y se utilizan sus datos guardados. Se comprobó la interacción local de los reportes. **La actualización contra un DW activo en esta PC queda pendiente de comprobar.** Ver números al abrir el archivo no demuestra que se haya conectado en ese momento.

## Para qué sirve cada hoja

| Hoja | Pregunta principal | Utilidad |
|---|---|---|
| `01_Resumen` | ¿Cómo evolucionan los ingresos y cuánto se vende? | Comparar años, identificar variaciones y consultar ingresos, facturas, unidades, clientes y promedio por factura |
| `02_Clientes` | ¿Qué clientes y países generan más ingresos? | Reconocer mercados y compradores destacados para orientar acciones comerciales |
| `03_Catalogo` | ¿Qué géneros, artistas y títulos tienen mayor demanda? | Comparar ingresos por género y artista y unidades vendidas por título |
| `04_Control` | ¿Los datos guardados mantienen los totales y las relaciones esperadas? | Revisar duplicados de detalle, referencias, importes y cantidades; mostrar el estado pendiente de la conexión |
| `05_Guia` | ¿Cómo se usa y cómo se explica el reporte? | Consultar instrucciones y límites dentro del propio libro |
| `06_Explorar` | ¿Cómo investigar otras preguntas con los mismos datos? | Manipular directamente una tabla dinámica y sus campos |

Los rankings ayudan a priorizar análisis; por sí solos no prueban que una campaña funcione ni que un producto sea rentable.

## Qué significan los indicadores

La tabla `fact_sales` tiene **una fila por detalle de factura**. Una factura puede contener varias líneas. Por eso contar las filas no equivale a contar facturas.

| Indicador | Cálculo | Resultado con todos los datos guardados |
|---|---|---:|
| Ingresos | Suma de `total_amount` de las líneas seleccionadas | 2.328,60 |
| Facturas | Conteo de `invoice_id` diferentes dentro de la selección | 412 |
| Líneas | Cantidad de filas de detalle | 2.240 |
| Unidades | Suma de `quantity` | 2.240 |
| Clientes | Conteo de `customer_key` diferentes con ventas seleccionadas | 59 |
| Pistas vendidas | Conteo de `track_key` diferentes con ventas seleccionadas | 1.984 |
| Promedio por factura | Ingresos seleccionados / facturas diferentes seleccionadas | 5,65 |
| Ingreso por cliente | Ingresos seleccionados / clientes con esas ventas | 39,47 |

Los importes están expresados en **la moneda de la fuente**. No se asigna una moneda que el modelo no identifica. El libro puede mostrar separadores decimales distintos según la configuración regional de Excel.

No hay información de costos para calcular ganancias o rentabilidad. Si se pregunta «¿cuánto se ganó?», este modelo permite responder cuánto se **vendió**, no cuál fue la utilidad.

Al filtrar un género, el promedio por factura utiliza únicamente las líneas de ese género y las facturas que las contienen. No representa necesariamente el importe completo de esas facturas.

## Cómo abrirlo y usarlo

Para reproducir esta entrega, usar Excel de escritorio en Windows con Power Query y Modelo de datos disponibles.

1. Abrir `Chinook_Reporte_Ejecutivo.xlsx`.
2. Empezar en `01_Resumen`. El libro contiene datos guardados y permite analizarlos sin actualizar desde PostgreSQL.
3. En el filtro **Año**, seleccionar `2009`. Los ingresos deben cambiar a **449,46** y las facturas a **83**.
4. Abrir `02_Clientes` o `03_Catalogo`: se conserva la selección de año. Los filtros se comparten entre las hojas.
5. Usar el icono de borrar filtro en cada segmentación para volver a todos los valores. La selección múltiple permite combinar opciones; las listas de países y géneros tienen desplazamiento.
6. Con todos los filtros borrados, seleccionar `USA` en país: los ingresos deben ser **523,06**. Borrar país y seleccionar `Rock` en género: deben ser **826,65**.
7. Antes de presentar el panorama general, borrar los tres filtros y comprobar nuevamente **2.328,60** de ingresos.

Los meses del gráfico mensual se numeran del 1 al 12. Si se seleccionan varios años, se acumula cada mes entre esos años. Para estudiar una secuencia mensual de un año concreto, seleccionar ese año.

Los indicadores superiores incluyen **toda la selección**, mientras los rankings muestran resultados destacados. No se debe esperar que la suma de un Top 10 sea el total general. Los empates pueden conservar más elementos en una tabla dinámica; la lista visible de títulos muestra diez posiciones según el orden del modelo.

La lista de títulos agrupa por `track_name`: distintas grabaciones con el mismo nombre se suman. El indicador «Pistas vendidas» sí cuenta identificadores `track_key` diferentes. El catálogo de Chinook también contiene video.

## Cómo está conectado

```text
CSV → ETL de Staging → chinook_staging
                            ↓
                        ETL del DW
                            ↓
                        chinook_dw
                            ↓
                   Power Query en Excel
                            ↓
                Modelo de datos relacionado
                            ↓
             Tablas dinámicas, filtros y gráficos
```

El libro conserva cinco consultas PostgreSQL:

| Tabla | Función | Filas guardadas |
|---|---|---:|
| `public.fact_sales` | Líneas e importes de venta | 2.240 |
| `public.dim_date` | Calendario para agrupar por año y mes | 1.826 |
| `public.dim_customer` | Datos del cliente, incluido su país | 59 |
| `public.dim_track` | Catálogo, géneros, artistas y formatos | 3.503 |
| `public.dim_employee` | Agente de soporte asociado | 8 |

En el Modelo de datos, `fact_sales` se relaciona con las dimensiones por `date_key`, `customer_key`, `track_key` y `employee_key`. Son cuatro relaciones: permiten que un filtro sobre una dimensión seleccione las ventas correspondientes.

La relación de empleado se completó en el nuevo libro; no se alteraron las bases de datos ni el archivo Excel anterior. El agente representa la asignación actual de soporte al cliente, no un vendedor histórico identificado en la factura.

Las consultas leen las cinco tablas directamente. Este libro **no necesita** crear `vw_ventas_excel`; esa vista del repositorio es una alternativa para otros análisis.

## Qué falta para demostrar la conexión al DW

El origen conservado es **`localhost:5432`**, base **`chinook_dw`**. Son los valores del archivo anterior; no detectan automáticamente la configuración de otra PC. `localhost` significa el equipo donde se abre Excel.

En la preparación local conocida, Staging usa `chinook_staging` en el puerto `5433`. Eso no prepara automáticamente `chinook_dw` ni cambia las conexiones de Excel. Un servidor PostgreSQL puede alojar ambas bases, pero el host, puerto y nombre utilizados por el DW deben coincidir con los de Excel.

Para probar el refresco:

El procedimiento completo, con ejemplos para los puertos `5432` y `5433`, acceso de compañeros y solución de errores, está en la [sección 9 del README](../README.md#9-capa-de-visualización-y-análisis-en-microsoft-excel).

1. Preparar y cargar el DW según las instrucciones del repositorio. Confirmar que sus cinco tablas ya tengan datos. Excel solo consulta lo que exista en el DW; no ejecuta el ETL por abrir el archivo.
2. Confirmar **host, puerto, nombre de base y usuario con lectura** del DW. Una cuenta de Staging no obtiene acceso al DW automáticamente. No se incluyen contraseñas en el libro.
3. Abrir **Datos → Consultas y conexiones**. Si el DW usa otro servidor o puerto, editar el paso `Source`/`Origen` de **las cinco consultas**. Por ejemplo, sustituir `localhost:5432` por `localhost:5433` solamente si allí se preparó realmente `chinook_dw`.
4. Mantener el nombre de base correcto en `PostgreSQL.Database("servidor:puerto", "chinook_dw")`. Si la base tiene otro nombre, modificar también ese argumento.
5. Introducir la autenticación de PostgreSQL cuando Excel la solicite. Si conserva otra cuenta, revisar **Datos → Obtener datos → Configuración de origen de datos → Editar permisos** para ese origen.
6. Ejecutar **Datos → Actualizar todo** y esperar a que terminen las cinco consultas. Confirmar que no haya errores; luego actualizar las tablas dinámicas si Excel lo requiere.
7. Borrar los filtros y revisar `04_Control`. Contrastar con el DW las 2.240 líneas, las 412 facturas diferentes y los 2.328,60 de ingresos de la fotografía original.
8. Guardar después de confirmar la actualización. Para la exposición, mostrar las consultas completadas y el cambio de los filtros con el DW disponible.

Si aparece un error de conexión y siguen viéndose números, se están viendo datos guardados. Eso no acredita un refresco correcto. Tampoco se trata de actualización continua: **Actualizar todo** toma una nueva lectura del DW; para incorporar cambios de Staging, primero debe actualizarse el DW mediante su ETL.

## Qué comprueba la hoja Control

La hoja revisa el **modelo completo**, sin los filtros comerciales. Espera los totales de la fotografía original de Chinook y verifica que no haya identificadores de detalle repetidos, referencias sin dimensión, cantidades/precios no positivos ni diferencias entre importe y precio por cantidad.

Un `OK` acredita ese control sobre los datos que tiene el libro. No demuestra por sí solo que PostgreSQL esté conectado ni que la conciliación Staging → DW se haya ejecutado. Esa conciliación pertenece a la validación del ETL del DW.

Si el conjunto de datos crece legítimamente, los totales fijos de referencia deberán actualizarse después de conciliar la nueva carga. Un cambio de volumen no debe confundirse automáticamente con un error.

## Cómo mostrar una tabla dinámica de verdad

Abrir `06_Explorar` y hacer clic dentro de la tabla. Desde **Analizar tabla dinámica → Lista de campos** se pueden explorar las dimensiones y medidas. Por defecto se comparan países mediante ingresos, facturas, unidades, clientes y promedio por factura.

Las otras once tablas dinámicas están en hojas auxiliares `TD_*`, ocultas para despejar la presentación. Se pueden mostrar con clic derecho en una pestaña → **Mostrar**. Los gráficos y las tarjetas están vinculados a esas tablas; las cifras no son valores escritos a mano.

Las hojas no están protegidas. Conviene guardar una copia antes de cambiar la estructura de las tablas dinámicas auxiliares, porque los indicadores visibles referencian sus celdas.

## Explicación breve para la exposición

> El DW organiza las ventas en una tabla de hechos y cuatro dimensiones. Excel consulta esas cinco tablas y usa sus relaciones para analizar los ingresos por fecha, cliente y catálogo. Las tablas dinámicas responden preguntas del negocio, y los filtros permiten cambiar la selección sin escribir nuevas consultas. Contamos las facturas por identificadores diferentes para no confundirlas con sus líneas. Los controles revisan que los totales y las relaciones sean coherentes. Los importes representan ventas; no calculamos ganancias porque no tenemos costos.

Después, demostrar un filtro, una tabla dinámica editable y un refresco exitoso con el DW activo. Esa demostración completa la parte de conexión que sigue pendiente en esta PC.
