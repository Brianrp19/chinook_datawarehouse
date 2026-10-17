# Bitácora de avance del proyecto Chinook

## Prioridad para mañana: separar el arranque de la página y la ejecución del ETL

Quiero revisar cómo levantar la página de Prefect sin ejecutar automáticamente las tareas del DW. Debo distinguir tres acciones: iniciar el servidor y la interfaz, iniciar el proceso `serve` que espera solicitudes y ejecutar el ETL mediante el botón Run.

La página puede estar disponible solo con el servidor encendido para consultar el historial. Para atender ejecuciones desde Run, también debe estar activo el proceso `serve`. Sin una programación automática, iniciar estos procesos no debe ejecutar la validación, transformación ni carga.

Mañana revisaré `src/levantar_pagina.py`, el punto de entrada de `src/etl_flow.py` y los comandos documentados para comprobar esta separación. El deployment apunta al flujo; el flujo es quien llama a las tareas. Quiero comprobar que los datos del DW solo se recarguen cuando solicite una ejecución y dejar claro qué terminal debe permanecer abierta para cada función.

Fecha de cierre de la sesión: 17 de octubre de 2026.

## Contexto y agenda de trabajo

Durante esta sesión revisé el proyecto de Minería de Datos y comparé lo que tenemos con el enunciado y la rúbrica del profesor. El trabajo comenzó el 16 de octubre y continuó durante la madrugada del 17. Mi intención fue entender el código y hacer los cambios paso a paso, con acompañamiento, para poder explicar después qué hace cada parte.

La herramienta asignada es Prefect. En nuestro proyecto, Prefect organiza y supervisa el ETL, pandas transforma los datos y PostgreSQL almacena el Data Warehouse. La página de Prefect sirve para ejecutar y revisar el proceso; los informes de ventas que pide el profesor se deben preparar en Excel conectado al DW.

La agenda fue revisar requisitos, corregir las validaciones, integrar los controles a Prefect, ejecutar la carga en Windows, proteger la transacción y habilitar la ejecución desde la página.

## Punto de partida

El proyecto ya tenía los once CSV de Chinook, el esquema SQL y las funciones de transformación y carga. No construí todo desde cero en esta sesión. El modelo es una estrella con cuatro dimensiones: fecha, cliente, empleado y canción. La tabla de hechos es `fact_sales` y su nivel de detalle es una línea de factura de `InvoiceLine`.

Las canciones se enriquecen con álbum, artista, género, formato y cantidad de listas en las que aparecen. El empleado asociado a una venta representa al agente de soporte asignado al cliente en la fuente, no necesariamente al vendedor histórico. La fuente no tiene un historial de esas asignaciones.

## Validación de los resultados del DW

Primero revisé `src/load.py`. La validación original comparaba contra números fijos y solamente imprimía una advertencia si algo salía mal. Eso permitía que Prefect indicara éxito aunque se detectaran diferencias.

Cambié la validación para leer `InvoiceLine.csv`, contar las filas esperadas y calcular el monto original con `Decimal`. Ahora los resultados esperados vienen de la fuente. También agregué `COALESCE` a la suma SQL para manejar una tabla de ventas vacía y cambié el comportamiento para lanzar `ValueError` cuando los conteos, montos o cálculos no coinciden. Así Prefect puede marcar la tarea como fallida.

Esta conciliación revisa cantidades y montos generales. No demuestra por sí sola que cada venta tenga exactamente todos los atributos correctos; una comparación registro por registro sería una comprobación adicional.

## Integridad de las fuentes

En `src/validar_integridad.py` organicé las revisiones dentro de una función. La validación comprueba identificadores nulos, claves duplicadas y relaciones entre los CSV. En `PlaylistTrack` la clave es la combinación de `PlaylistId` y `TrackId`.

También revisé la relación del supervisor de los empleados. Se permite que `ReportsTo` esté vacío para quien no tenga supervisor, pero si contiene un identificador, este debe existir. Aprendí que no todos los nulos son errores y que las reglas dependen del significado de cada campo.

La función acumula los problemas encontrados y lanza un error si existe alguno. La conecté a una tarea de Prefect antes de transformar. Esto evita que una unión elimine ventas con referencias inexistentes y que el problema se descubra solamente después de cargar el DW.

## Calidad y reglas de negocio

Después adapté `src/validar_calidad_negocio.py` para que también se pueda llamar desde Prefect. Las revisiones incluyen precios y cantidades positivos, duración de canciones, fechas válidas, contratación posterior al nacimiento, campos críticos sin nulos y coincidencia entre el total de cada factura y sus líneas. Agregué el control de cantidades enteras y corregí la comparación para detectar facturas sin correspondencia, además de montos distintos.

Durante la implementación apareció un error por escribir `.isna` en vez de `.isna()`. Entendí que los paréntesis ejecutan el método y producen las condiciones que necesita pandas. Una vez corregido, la tarea terminó correctamente.

Los correos duplicados se muestran como información. No se usan como claves del DW. Tampoco hace falta rellenar indiscriminadamente todos los valores vacíos.

## Instalación y conexión en Windows

Al ejecutar las validaciones, el entorno virtual no tenía pandas. Instalé las dependencias y pude correr los scripts. Después la carga falló porque la configuración por defecto apuntaba a una ruta de PostgreSQL de Linux.

Configuré el archivo `.env` para usar `localhost`, el puerto 5432, el usuario local y la base `chinook_dw`. La contraseña permanece en ese archivo local y no debe incluirse en esta bitácora ni subirse a Git. Se comprobó que Git ignora `.env`.

El siguiente error indicó que no existía `chinook_dw` en esa instalación. Después de crear la base y aplicar `sql/create_dw.sql`, el ETL logró conectarse, cargar y validar los datos.

## Protección de la carga

La carga anterior confirmaba el vaciado antes de insertar las tablas. Si algo fallaba después, el DW podía quedar vacío o incompleto.

En `task_cargar()` coloqué el vaciado, la carga y la validación dentro del mismo `with engine.begin() as conn`. Pasé esa misma conexión a `load_data()` y `verify_dw_data()`. Adapté la validación con `Connection` y `nullcontext` para reutilizar la conexión sin cerrarla.

Ahora, si una operación lanza un error dentro de ese bloque, la transacción se revierte. Si el bloque termina correctamente, se confirma. La validación final independiente se conserva para revisar los datos ya guardados.

Corregí dos errores durante este cambio: usar `ConnectionError` en vez de `conn` y dejar la carga fuera del bloque por la sangría. La ejecución posterior terminó correctamente. Para la versión actual todavía queda documentar una prueba controlada de fallo y reversión; una ejecución exitosa no demuestra ese caso.

Queda un detalle pequeño: el mensaje de transacción confirmada está dentro del `with`. Conviene moverlo después del bloque para que se imprima cuando la confirmación ya haya terminado. También conviene revisar si necesitamos `CASCADE`, porque las cinco tablas ya se enumeran en el vaciado.

Esta protección se implementó en el camino de `etl_flow.py`. La ejecución directa de `load.py` todavía tiene su propio procedimiento y conviene unificarlo o dejar claramente documentado cuál es el punto de entrada oficial.

## Resultados comprobados

Las ejecuciones completas mostraron 1.826 fechas, 8 empleados, 59 clientes, 3.503 canciones y 2.240 líneas de venta. El total fue de $2.328,60 y se detectaron cero inconsistencias matemáticas. Los conteos y montos coincidieron con la fuente.

Probé consultas SQL de control y análisis: conteos, relaciones faltantes, duplicados, calendario, ventas mensuales, rankings y participación por país. También ejecuté una consulta de artistas por país y año con crecimiento y funciones de ventana. Entendí que los empates pueden mostrar más de tres artistas y que el crecimiento vacío de 2009 corresponde a la falta de datos de 2008, no a un dato que haya que limpiar.

## Uso de la página de Prefect

Al principio el flujo iniciaba un servidor temporal que se apagaba al terminar. La página que estaba revisando no mostraba esas ejecuciones. Configuré un servidor local en el puerto 4201 porque el puerto inicial estaba ocupado.

Agregué `PREFECT_API_URL=http://127.0.0.1:4201/api` al `.env` y cambié el final de `etl_flow.py` a `etl_chinook.serve(name="chinook-local", limit=1)`. Esto registra el deployment y deja el proceso esperando solicitudes. El límite permite una ejecución simultánea mediante ese proceso para evitar recargas superpuestas.

Pude ver `chinook-local` en Deployments e iniciar el ETL desde Run. La captura mostró una ejecución en Completed con cinco tareas. Dejé los comandos de arranque y cierre en `comandosPrefect.md`.

Para usarlo necesito PostgreSQL encendido, una terminal con el servidor de Prefect y otra con el proceso que atiende el deployment. El `.env` indica a qué servidor conectarse, pero no lo inicia automáticamente.

## Dónde quedé

Quedé con el ETL funcionando en PostgreSQL y disponible para ejecutarlo desde la página de Prefect. El flujo hace integridad, calidad de negocio, transformación, carga con validación dentro de la transacción y comprobación final del DW.

Decidí dejar los reintentos automáticos para después porque las últimas ejecuciones no mostraron errores de conexión. No están implementados en la versión actual. Las mejoras que inicialmente se aplicaron directamente con ayuda se revirtieron y después fui incorporando los cambios explicados paso a paso.

El historial local revisado todavía mostraba los commits anteriores del 4 y 13 de octubre. Me falta guardar estos avances en Git y mantener evidencia del trabajo de cada integrante. Este archivo es una bitácora de apoyo, no reemplaza el documento final APA 7.

## Pendientes según lo que pide el profesor

El siguiente paso principal es definir las preguntas del negocio y preparar los informes en Excel conectado al DW. Todavía no encontré esos entregables en los archivos revisados; si el equipo los tiene por fuera, hay que incorporarlos a la revisión.

Tengo pendiente documentar el problema de Invacom, quiénes usarán la información, sus necesidades y los objetivos generales y específicos con metas medibles. Esto debe justificar qué analizamos y por qué elegimos las dimensiones y medidas actuales.

Para Excel puedo empezar con ventas por año y mes, país del cliente, género, artista y cliente. Antes debo preparar las consultas o vistas necesarias, conectar Excel a PostgreSQL y crear tablas dinámicas que respondan a las preguntas de negocio. No basta con copiar resultados estáticos: el enunciado pide conexión al DW.

Debo elaborar un solo documento en formato APA 7 con portada, introducción, enlace al repositorio, enunciado del problema, objetivo general, objetivos específicos, descripción de la solución, diagrama dimensional, conclusión y bibliografía. También debo explicar los fundamentos de ETL y DW, las fuentes, las reglas de calidad y las decisiones del modelo. El README sirve de base técnica, pero no sustituye ese documento.

Debo preparar un diagrama dimensional claro con tablas, claves, relaciones, medidas y granularidad. El esquema y la explicación ya existen, pero falta asegurar que el diagrama final quede adecuado para el informe y la exposición.

El profesor exige Git, aportes de todos los integrantes y avances semanales. Debemos guardar evidencias reales y continuas. También exige Scrum con sprints semanales, un Scrum Master, tablero Kanban, planificación y revisiones. No se verificó un tablero externo durante esta sesión, así que tengo que confirmar qué existe y documentarlo. Además, debo confirmar el coordinador del equipo y la organización de los aportes individuales.

Finalmente, falta preparar la defensa presencial con intercambio de roles. Debemos poder explicar el modelo, el proceso de carga, las reglas de calidad, el uso de Prefect y el valor de los informes. La asistencia presencial es obligatoria según el enunciado.

## Agenda para continuar

Primero guardaré los cambios y las evidencias de ejecución en Git. Después revisaré las preguntas de negocio con el equipo y prepararé las vistas o consultas para Excel. Continuaré con la conexión y las tablas dinámicas, el documento APA 7 y la organización de evidencias de Scrum. Antes de dar por cerrada la parte técnica, revisaré el script de compatibilidad del modelo y documentaré una prueba de error que compruebe la reversión de la transacción.

Como referencia, la rúbrica asigna 20% al modelo dimensional, 35% al ETL, 10% al DW y Excel, 5% a documentación, 5% a Git, 5% a Scrum y 20% a la defensa. Tener el ETL funcionando es un avance importante, pero todavía no significa que todo el proyecto esté terminado.
