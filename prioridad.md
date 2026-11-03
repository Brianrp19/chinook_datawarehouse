# Pendientes para dejar listo Chinook Data Warehouse

Fecha de revisión: 3 de noviembre de 2026.

## Actualizacion tras la primera carga completa

Se confirmo que las cinco tablas del DW no exist?an. Se crearon a partir de `sql/create_dw.sql`, omitiendo los DROP y verificando antes la ausencia de relaciones con esos nombres. Despu?s se ejecut? `src/etl_flow.py --run-once` y finaliz? en Completed.

- Ejecuci?n: `rose-kingfisher`, ID `2a71ed3b-5df9-4894-9442-b241d6faf044`.
- Dashboard: http://127.0.0.1:4200/runs/flow-run/2a71ed3b-5df9-4894-9442-b241d6faf044
- Staging: 11 tablas, 15.607 filas; integridad y negocio aprobados.
- DW: dim_date 1.826; dim_employee 8; dim_customer 59; dim_track 3.503; fact_sales 2.240 filas.
- Total fuente y DW: 2.328,60; inconsistencias matem?ticas: 0.

Quedan resueltos la inicializaci?n del esquema y la primera carga real. Siguen pendientes la repetici?n de carga, las pruebas de rollback, el lector restringido, Excel y las mejoras del c?digo. Las menciones de tablas ausentes y carga pendiente en la revisi?n siguiente describen el diagn?stico anterior a esta correcci?n.

## Estado real del proyecto (revisi?n anterior a la primera carga)

El proyecto tiene implementados la extracción de Staging, el modelo dimensional, las transformaciones, las validaciones de integridad y negocio, la carga orquestada con Prefect y un libro de Excel. Todavía no está comprobado el funcionamiento completo de extremo a extremo.

Esta revisión se basa en el código y en la ejecución de `scripts/check_environment.py`. No se ejecutó la carga, no se reconstruyeron tablas y no se verificó el libro de Excel en esta revisión. Los resultados del README son valores de referencia, no evidencia de una ejecución local completada.

## 1. Lo que ya está resuelto o comprobado

- [x] Python 3.13.17 funciona en `.venv` y las dependencias están instaladas.
- [x] Se corrigió la incompatibilidad de arranque con FastAPI fijando `fastapi==0.142.2` en `requirements.txt`; `pip check` pasó durante la corrección.
- [x] Existe `.env`, excluido de Git.
- [x] Staging autentica y permite consultar sus 11 tablas: los conteos individuales coinciden con el contrato, con 15.607 filas en total.
- [x] La conexión a `chinook_dw` autentica.
- [x] La API de Prefect configurada responde a la comprobación de salud.
- [x] El flujo de Prefect ya contiene validaciones de integridad y negocio antes de transformar.
- [x] La ruta de carga de Prefect agrupa TRUNCATE, inserción y conciliación en una transacción y utiliza los datos extraídos al inicio.
- [x] El SQL define claves primarias, claves foráneas, unicidad de `invoice_line_id` y restricciones de cantidades, precios e importes.

## 2. Prioridad inmediata: conseguir una ejecución completa

### 2.1 Corregir el acceso a Staging

**Hallazgo confirmado:** `STG_USER` está configurado como `postgres`. La comprobación detecta permiso de escritura y de creación en el esquema para las 11 tablas. La conexión funciona, pero incumple el acceso de solo lectura definido en el proyecto.

- [ ] Provisionar o corregir el usuario `chinook_stg_reader` en el servidor que contiene Staging.
- [ ] Conceder acceso de conexión, uso del esquema y SELECT sobre las fuentes; revisar permisos heredados, propiedad y privilegios elevados para impedir escritura y creación.
- [ ] Configurar ese usuario y su contraseña real en `.env`, sin compartir ni versionar la contraseña.
- [ ] Volver a ejecutar el comprobador: todas las fuentes deben pasar los controles de permisos y conteos.

**Aclaración:** actualmente Staging está configurado en `127.0.0.1:5432`. Esto puede funcionar con dos bases separadas en la misma instancia. Debe decidirse si la entrega requiere además dos motores independientes, como afirma el README; no cambiar a 5433 sin tener un servidor real allí.

### 2.2 Inicializar o completar el esquema del DW

**Hallazgo confirmado:** `dim_date` no existe en `public` de la base consultada. El comprobador se detiene en esa primera tabla ausente, por lo que todavía no permite afirmar si existen las otras cuatro.

- [ ] Inventariar las tablas y los datos actuales del DW antes de reconstruir.
- [ ] Crear las cinco tablas y sus restricciones mediante `sql/create_dw.sql` cuando corresponda.
- [ ] Comprobar que las cinco tablas tengan exactamente las columnas esperadas por la transformación.

**Precaución concreta:** `create_dw.sql` ejecuta DROP TABLE ... CASCADE. Si hay datos o vistas que conservar, respaldarlos y planificar la reconstrucción primero.

### 2.3 Unificar Prefect y dejar un arranque reproducible

**Hallazgo confirmado:** `.env` sigue apuntando a `http://127.0.0.1:4200/api`, y esa API responde. Las instrucciones del proyecto indican 4201. No está comprobado que ambos puertos correspondan al mismo servidor ni al mismo historial.

En esta sesión también apareció una revisión desconocida en la base global `C:\Users\migue\.prefect\prefect.db`. Se preparó una base separada en `.prefect` dentro del proyecto y sus migraciones pasaron; eso no demuestra que el servidor activo esté usándola.

- [ ] Elegir un único servidor para Staging y DW y dejar la misma URL en las terminales y `.env`.
- [ ] Documentar el PREFECT_HOME y la conexión interna elegidos para que los siguientes arranques usen el mismo historial.
- [ ] Verificar arranque completo, dashboard y registro de una ejecución real; crear la aplicación en memoria no sustituye comprobar su arranque.
- [ ] Mantener la base interna y los perfiles locales fuera de Git.

### 2.4 Completar la primera ejecución

- [ ] Ejecutar `python src/etl_flow.py --no-load` y resolver cualquier error de datos o transformación.
- [ ] Con el esquema listo, ejecutar `python src/etl_flow.py --run-once`.
- [ ] Comprobar conteos, total monetario, restricciones y estado Completed en Prefect.
- [ ] Repetir la carga y comprobar que no duplica registros.

**Cierre de esta prioridad:** acceso lector correcto, esquema completo y carga real finalizada con conciliación satisfactoria.

## 3. Corregir problemas del código antes del cierre técnico

### 3.1 El validador del modelo no valida el resultado transformado

**Hallazgo confirmado:** `src/validar_modelo_dw.py` extrae datos al importar el módulo e imprime comprobaciones sobre fuentes. No ofrece una función que valide los cinco DataFrames de destino, ni está integrado en `etl_flow.py`.

- [ ] Convertirlo en funciones sin consultas durante la importación.
- [ ] Comprobar columnas, tipos, nulos, claves únicas, relaciones, longitudes VARCHAR y rangos NUMERIC/enteros contra el DDL.
- [ ] Lanzar errores identificando tabla, columna y regla.
- [ ] Ejecutarlo después de transformar, tanto en `--no-load` como antes de cargar.

### 3.2 Hay dos caminos de carga con garantías diferentes

**Hallazgo confirmado:** Prefect usa una transacción para vaciar, cargar y conciliar. En cambio, `src/load.py` ejecutado directamente transforma, inserta con append y valida después, sin el mismo vaciado ni una única transacción común. Tampoco ejecuta las mismas validaciones previas; una repetición puede fallar por claves ya existentes y no ofrece la misma protección frente a una carga parcial.

- [ ] Compartir una única función de carga transaccional entre ambos caminos, o retirar la ejecución directa como opción operativa.
- [ ] Aplicar las mismas validaciones y conciliar contra la misma extracción.
- [ ] Liberar el motor del camino directo y el de `task_validar` con `finally`.
- [ ] Verificar rollback mediante un fallo controlado en una base de pruebas y comprobar que se conserva el estado previo.

### 3.3 La extracción no aplica todo el contrato

**Hallazgo confirmado:** el extractor verifica 11 tablas y 15.607 filas globales, pero no compara el conteo individual de cada fuente con el contrato. El comprobador de entorno sí lo hace. Las conversiones están duplicadas en código y `ReportsTo` usa `errors="coerce"`, que puede convertir una referencia inválida en un nulo permitido.

- [ ] Validar fuentes, columnas y conteos individuales durante la extracción habitual.
- [ ] Rechazar valores no vacíos inválidos en `ReportsTo` antes de convertirlos a nulos.
- [ ] Comprobar que los enteros no tengan fracciones antes de convertirlos; la validación posterior de Quantity no recupera una fracción perdida en la extracción.
- [ ] Centralizar el contrato y documentar que sus conteos fijos corresponden al conjunto de referencia.
- [ ] Aclarar que STG_SCHEMA no cambia las consultas canónicas: el esquema lo determina el contrato.

### 3.4 Falta endurecer la precisión monetaria

**Hallazgo confirmado:** la extracción y transformación usan float; la validación de facturas admite diferencias de hasta un centavo, aunque su mensaje habla de coincidencia exacta. La conciliación global del DW usa Decimal y compara exactamente, pero eso no elimina los redondeos anteriores.

- [ ] Usar Decimal o centavos enteros para el cálculo monetario de extremo a extremo.
- [ ] Definir y validar la precisión admitida antes de redondear.
- [ ] Rechazar precios y totales no finitos y valores numéricos inválidos.
- [ ] Alinear las reglas y los mensajes de validación con la precisión elegida.

### 3.5 La conciliación del DW es insuficiente para algunas diferencias

**Hallazgo confirmado:** `verify_dw_data` exige conteo de ventas, total global y consistencia de precio por cantidad. Los conteos de dimensiones y el número de pistas con playlists se imprimen, pero no se comparan con los resultados transformados. Las restricciones SQL ya cubren unicidad y referencias, pero no demuestran que cada venta tenga la dimensión correcta.

- [ ] Comparar todas las dimensiones con la transformación esperada.
- [ ] Conciliar por factura y por `invoice_line_id`, incluyendo cliente, pista, empleado y fecha.
- [ ] Verificar continuidad del calendario y `playlist_count` contra las asociaciones de origen.
- [ ] Corregir el caso `source_data` suministrado sin InvoiceLine/invoice_line: actualmente puede dejar sin definir los valores esperados; debe producir un error claro.

## 4. Verificar Excel y los resultados de negocio

**Estado:** existen `ecxel/Chinook_Analisis_DataWarehouse.xlsx` y `Book1.xlsx`. Su existencia no comprueba conexiones, relaciones ni actualización. El libro no se inspeccionó en esta revisión.

- [ ] Elegir y documentar el libro final de entrega.
- [ ] Confirmar que sus cinco consultas de Power Query leen el DW correcto con credenciales locales válidas.
- [ ] Revisar relaciones con las claves `date_key`, `customer_key`, `employee_key` y `track_key`.
- [ ] Ejecutar Datos → Actualizar todo después de cargar el DW.
- [ ] Comparar ventas, cantidades y filtros por fecha, país, género y empleado contra SQL.
- [ ] Comprobar tablas dinámicas, gráficos y KPIs en el equipo de presentación.
- [ ] Si se usa `vw_ventas_excel`, crearla con `sql/vista_excel.sql`; no está incluida en `create_dw.sql`.

**Cierre:** el reporte se actualiza desde PostgreSQL y sus resultados coinciden con SQL sin duplicar ventas.

## 5. Documentación y entrega

- [ ] Corregir README y ENTORNO_LOCAL: actualmente describen versiones, puertos y estados que no coinciden con el entorno revisado.
- [ ] Documentar si se usan dos bases en PostgreSQL 18 o dos motores separados; confirmar que la arquitectura cumple el requisito académico.
- [ ] Corregir el README: las relaciones del DW usan `*_key`, no los identificadores operacionales `*_id`.
- [ ] Aclarar que `unit_price` no es una medida aditiva; quantity y total_amount sí lo son al grano de línea.
- [ ] Ajustar las afirmaciones sobre validación del modelo, conciliación exacta y creación de la vista a lo realmente implementado.
- [ ] Documentar preparación y ejecución completa en PowerShell, incluyendo recuperación de los problemas de dependencias y almacenamiento de Prefect encontrados.
- [ ] Permitir consultar `--help` sin comprobar antes la disponibilidad de Prefect.
- [ ] Resolver si Linux forma parte de la entrega: los scripts run_etl.sh, setup_local.sh y stop_local_postgres.sh aparecen eliminados en el árbol actual; no tiene sentido dejar tareas de reparación de archivos ausentes sin decidir su alcance.
- [ ] Marcar planes anteriores como históricos o actualizarlos para evitar instrucciones contradictorias.
- [ ] Confirmar con el profesor qué significa el requisito «MS» pendiente en plan_reorganizacion.md y si exige trabajo adicional.
- [ ] Revisar cambios de Git y excluir credenciales, bases internas, archivos temporales y logs sensibles.
- [ ] Guardar evidencia sin secretos: fecha, versión, comandos, conteos, conciliación, ejecución Completed y actualización del reporte.

## 6. Pruebas que faltan para respaldar la entrega

No se encontraron archivos de pruebas automatizadas en la búsqueda del repositorio.

- [ ] Probar rechazo de claves duplicadas/huérfanas, fechas inválidas, fracciones en enteros, importes inválidos y textos fuera del límite SQL.
- [ ] Probar que una referencia ReportsTo inválida no se pierda como nulo.
- [ ] Probar diferencias por línea/factura aunque el total global coincida.
- [ ] Probar carga repetida y rollback en un entorno de pruebas.
- [ ] Ejecutar el recorrido real Staging → DW → Excel y conservar los resultados.

## 7. Orden recomendado y condición de proyecto listo

1. Corregir el lector de Staging y definir la arquitectura local.
2. Revisar e inicializar el esquema del DW.
3. Unificar el servidor y la configuración de Prefect.
4. Completar auditoría y una carga real.
5. Corregir validador del modelo, carga directa, conversiones y conciliación.
6. Repetir las verificaciones con pruebas de fallo y repetición.
7. Actualizar Excel y contrastarlo con SQL.
8. Cerrar documentación, requisitos académicos y evidencia de entrega.

Para una demostración funcional hacen falta, como mínimo, conexiones correctas, esquema, auditoría, carga y Excel actualizado. Para dar por terminada la entrega técnica también deben cerrarse las garantías de validación, permisos, transacciones y reproducibilidad descritas arriba.

| Control de aceptación del conjunto de referencia | Resultado esperado |
|---|---:|
| Fuentes Staging | 11 tablas / 15.607 filas |
| dim_date | 1.826 filas: 2009-01-01 a 2013-12-31 |
| dim_employee | 8 filas |
| dim_customer | 59 filas |
| dim_track | 3.503 filas |
| fact_sales | 2.240 filas |
| Ventas totales | 2.328,60 |
| Diferencia monetaria contra la fuente | 0,00 |
| Claves duplicadas o huérfanas | 0 |
| Inconsistencias matemáticas | 0 |

Estos resultados del DW siguen pendientes de comprobar en una carga real. El proyecto queda listo cuando se demuestra el recorrido completo, la carga es repetible y atómica, el lector está restringido, Excel coincide con SQL y otra persona puede reproducir el procedimiento con la documentación.
