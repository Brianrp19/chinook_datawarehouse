# Prioridades para completar Chinook Data Warehouse

Fecha de revisión: 2 de noviembre de 2026.

Esta lista parte de la revisión del código, SQL, scripts y documentación. Los resultados publicados en el README aún deben comprobarse mediante una ejecución en el entorno configurado.

## P0 — Preparar el entorno de validación

- [x] Disponer de Python funcional y crear el entorno virtual `.venv`.
- [ ] Instalar las dependencias de `requirements.txt` y comprobar que sus versiones se pueden instalar juntas.
- [ ] Crear `.env` desde `.env.example` con las conexiones locales de Staging, DW y Prefect. Mantener las credenciales fuera de Git.
- [ ] Comprobar acceso de lectura a las 11 tablas de Staging y los permisos del usuario lector.
- [ ] Comprobar acceso a PostgreSQL DW y al servidor compartido de Prefect.
- [ ] Confirmar si el DW contiene datos que se deban conservar antes de reconstruir el esquema. `sql/create_dw.sql` elimina las tablas existentes.

**Criterio de cierre:** las conexiones funcionan y se puede ejecutar el modo de auditoría sin escribir en el DW.

### Avance de preparación local

- Python 3.12.10 instalado para el usuario y entorno `.venv` creado.
- `.env` creado desde la plantilla y excluido de Git. Faltan las credenciales reales y confirmar la ubicación de Staging.
- PostgreSQL 18 responde en `127.0.0.1:5432`; la autenticación y los datos existentes aún no están verificados.
- Sin respuesta en los puertos locales `5433` (Staging) y `4201` (Prefect) durante la comprobación inicial.
- Comprobador de conexiones de solo lectura: `.\.venv\Scripts\python.exe scripts/check_environment.py`.
- No ejecutar `sql/create_dw.sql` hasta comprobar si hay datos que deban conservarse.

## P1 — Corregir y unificar la carga segura

- [ ] Centralizar la carga para que Prefect y la ejecución directa de `src/load.py` usen la misma implementación.
- [ ] Ejecutar las validaciones de integridad, negocio y modelo antes de cargar por cualquiera de los caminos disponibles.
- [ ] Mantener el vaciado, la inserción y la conciliación dentro de una única transacción.
- [ ] Conciliar contra los mismos datos extraídos al inicio de la ejecución.
- [ ] Liberar las conexiones y los motores de base de datos al finalizar, incluso cuando haya errores.

**Criterio de cierre:** una carga fallida conserva el estado anterior del DW; ejecutar dos veces el proceso produce los mismos datos, sin duplicados.

## P2 — Implementar la validación del modelo transformado

- [ ] Convertir `src/validar_modelo_dw.py` en funciones reutilizables, sin consultar Staging al importar el módulo.
- [ ] Validar los cinco DataFrames transformados antes de escribir en PostgreSQL.
- [ ] Comprobar columnas requeridas, tipos, nulos, claves únicas y relaciones entre dimensiones y hechos.
- [ ] Comprobar longitudes de texto y rangos numéricos frente a `sql/create_dw.sql`.
- [ ] Rechazar los errores con mensajes que identifiquen tabla, columna y regla incumplida.
- [ ] Integrar esta validación tanto en el modo `--no-load` como en la carga completa.

**Criterio de cierre:** un dato incompatible con el esquema se detecta antes de iniciar la carga.

## P3 — Reforzar la extracción y las reglas de negocio

- [ ] Comprobar nombres de fuentes, columnas y conteos individuales con `contracts/staging_sources.json`.
- [ ] Obtener los valores de control del contrato para evitar referencias duplicadas en el código.
- [ ] Rechazar valores numéricos inválidos sin convertirlos silenciosamente en nulos, especialmente `Employee.ReportsTo`.
- [ ] Validar que los campos enteros no tengan fracciones antes de convertirlos.
- [ ] Rechazar importes no finitos y definir la precisión monetaria aceptada.
- [ ] Usar `Decimal` o centavos enteros para conciliar importes de forma exacta y eliminar la tolerancia actual de un centavo.
- [ ] Aclarar que los conteos fijos corresponden al conjunto Chinook de referencia; documentar qué cambiar si se admiten nuevos datos.

**Criterio de cierre:** cada fuente cumple el contrato y las anomalías se rechazan sin perder información durante la conversión.

## P4 — Completar la conciliación del DW

- [ ] Comparar los conteos de todas las dimensiones con los resultados esperados de la transformación.
- [ ] Comprobar que cada línea de factura aparezca exactamente una vez en `fact_sales`.
- [ ] Conciliar importes por factura y verificar la correspondencia de cliente, pista, empleado y fecha por línea.
- [ ] Comprobar cobertura y continuidad de la dimensión fecha.
- [ ] Verificar `playlist_count` contra las asociaciones únicas de Staging, incluyendo pistas sin listas si el contrato las admite.
- [ ] Conservar la comprobación del total global y de `total_amount = unit_price * quantity`.

**Criterio de cierre:** la validación detecta diferencias por registro o dimensión aunque el conteo y el importe global coincidan.

## P5 — Actualizar los scripts operativos

- [ ] Corregir `scripts/run_etl.sh` para invocar una modalidad válida del flujo, como `--run-once`.
- [ ] Evitar que `scripts/setup_local.sh` sobrescriba un `.env` existente.
- [ ] Incorporar la configuración de Staging y Prefect al procedimiento Linux.
- [ ] Separar la preparación del entorno de la reconstrucción destructiva del esquema.
- [ ] Mantener instrucciones completas de ejecución en PowerShell para el entorno Windows.
- [ ] Revisar que la ayuda de la CLI pueda consultarse sin depender de la disponibilidad del servidor Prefect.

**Criterio de cierre:** las instrucciones y los scripts permiten preparar y ejecutar el proyecto sin pasos implícitos ni pérdida accidental de configuración.

## P6 — Verificar Excel y la vista analítica

- [ ] Crear `vw_ventas_excel` mediante `sql/vista_excel.sql` cuando se utilice esta alternativa de consulta.
- [ ] Comprobar las cinco consultas de Power Query del libro principal y sus conexiones al DW correcto.
- [ ] Verificar las relaciones del modelo de Excel usando las claves `*_key`.
- [ ] Comprobar KPIs, tablas dinámicas, filtros y gráficos.
- [ ] Ejecutar **Datos → Actualizar todo** y contrastar los resultados con consultas SQL.
- [ ] Confirmar que el libro se puede abrir y actualizar en el equipo de presentación con el controlador requerido.

**Criterio de cierre:** Excel refleja los datos actuales del DW y sus indicadores coinciden con SQL, sin duplicar ventas.

## P7 — Agregar pruebas y guardar evidencia

- [ ] Agregar pruebas de rechazo de duplicados, claves huérfanas, fechas inválidas, cantidades fraccionarias e importes incorrectos.
- [ ] Agregar pruebas de límites de texto y conversiones numéricas inválidas.
- [ ] Probar el rollback provocando un fallo controlado en una base de pruebas.
- [ ] Probar la repetición de la carga y la conciliación por factura o línea.
- [ ] Ejecutar el flujo completo desde Staging hasta DW y actualizar Excel.
- [ ] Guardar un reporte de ejecución sin credenciales, con fecha, comandos, conteos, importes y resultado de las validaciones.

**Criterio de cierre:** las pruebas pasan y existe evidencia reproducible del funcionamiento completo.

## P8 — Corregir documentación y cerrar la entrega

- [ ] Actualizar el README para que describa las validaciones realmente implementadas y su orden.
- [ ] Corregir las referencias a claves foráneas: el modelo usa `date_key`, `customer_key`, `employee_key` y `track_key`.
- [ ] Corregir la descripción de medidas: `unit_price` no es aditiva; `quantity` y `total_amount` sí lo son al grano definido.
- [ ] Documentar que la vista de Excel se crea con un script separado.
- [ ] Documentar los comandos de auditoría, carga completa y servicio, además de sus requisitos.
- [ ] Actualizar o marcar como histórico `plan_reorganizacion.md` para evitar instrucciones contradictorias.
- [ ] Confirmar el requisito académico pendiente sobre «MS» registrado en el plan y resolverlo si forma parte de la entrega.
- [ ] Revisar que Git no incluya credenciales, archivos temporales ni registros sensibles.

**Criterio de cierre:** otra persona puede preparar, ejecutar y verificar el proyecto siguiendo únicamente la documentación.

## Valores de referencia para la aceptación final

Estos valores corresponden al conjunto Chinook documentado. Deben verificarse en una ejecución real:

| Control | Resultado esperado |
|---|---:|
| Fuentes de Staging | 11 tablas |
| Filas totales de Staging | 15.607 |
| `dim_date` | 1.826 filas, del 2009-01-01 al 2013-12-31 |
| `dim_employee` | 8 filas |
| `dim_customer` | 59 filas |
| `dim_track` | 3.503 filas |
| `fact_sales` | 2.240 filas |
| Total de ventas | 2.328,60 |
| Diferencia monetaria con la fuente | 0,00 |
| Duplicados y claves huérfanas | 0 |
| Inconsistencias matemáticas | 0 |

**Proyecto listo:** todas las prioridades cerradas, pruebas satisfactorias, carga repetible y atómica, Excel actualizado y documentación consistente con la implementación.
