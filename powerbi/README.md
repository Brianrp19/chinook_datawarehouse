# Proyecto 2 — Grupo Innova / Chinook

Este informe de Power BI continúa el Proyecto 1. Consulta las cinco tablas de `chinook_dw` en PostgreSQL y calcula los ocho KPIs del documento aprobado por el profesor. No utiliza los Excel del proyecto como fuente.

## Abrir y actualizar

1. Mantener las carpetas `Proyecto2_Innova.Report` y `Proyecto2_Innova.SemanticModel` junto al archivo `Proyecto2_Innova.pbip`. Descargar la carpeta completa; el `.pbip` por sí solo no contiene el informe.
2. Abrir `Proyecto2_Innova.pbip` en Power BI Desktop. El proyecto fue preparado con Desktop 2.159.1231.0. Si Desktop pide habilitar proyectos de Power BI, hacerlo en **Archivo → Opciones y configuración → Opciones → Características de versión preliminar**, reiniciar y abrir el proyecto.
3. El servidor predeterminado es `localhost:5432` y la base es `chinook_dw`. Si cambian, usar **Transformar datos → Administrar parámetros** y editar `Servidor` y `BaseDatos`. Estos valores identifican el DW, no el servidor de Prefect ni la base de Staging.
4. En **Inicio → Actualizar**, seleccionar autenticación **Base de datos** e introducir una cuenta con lectura sobre las cinco tablas. En tu instalación existe `chinook_dw_loader`; para compartir se recomienda una cuenta lectora. La contraseña se introduce en Power BI y no se incluye en el repositorio. El `.env` de Python no configura las credenciales de Power BI.
5. Para la instalación local sin TLS, Power BI puede indicar que no consigue cifrar la conexión. La opción de continuar corresponde únicamente al servidor local de esta práctica. Para un servidor remoto, configurar TLS con su administrador.
6. Si solicita niveles de privacidad, asignar **Organizacional** al origen PostgreSQL. No es necesario desactivar los controles de privacidad.
7. Esperar a que termine la actualización y elegir un único **Mes de análisis**. La selección inicial es diciembre de 2013; son datos históricos, por lo que seleccionar el mes actual no mostraría ventas.

El modo es **Importación**: cada actualización vuelve a consultar el DW y guarda una copia en el modelo de Power BI. Los filtros responden inmediatamente sobre esa copia. Un cambio en PostgreSQL aparece después de **Actualizar**; esto no es una conexión de tiempo real ni un proceso que recargue Staging o el DW.

En otra computadora, `localhost` significa **esa otra computadora**. El compañero debe tener su propio `chinook_dw` cargado o indicar la dirección de un servidor compartido accesible. No necesita usar tu contraseña ni copiar tu `.env`.

## Requisitos del DW y acceso

La base debe estar creada y cargada mediante el Proyecto 1. Power BI no crea tablas, no corre Prefect y no ejecuta el ETL.

| Tabla de PostgreSQL | Tabla en Power BI | Función |
|---|---|---|
| `public.fact_sales` | `Ventas` | Una fila por línea de factura; cantidades e importes. |
| `public.dim_date` | `Fecha` | Calendario y agrupación mensual. |
| `public.dim_customer` | `Clientes` | Identidad y geografía del comprador. |
| `public.dim_track` | `Canciones` | Contenido, artista, género y álbum. |
| `public.dim_employee` | `Empleados` | Empleado de soporte asignado al cliente. |

El contrato es el esquema definido por `../sql/create_dw.sql`. Las consultas seleccionan columnas concretas; si se cambia el nombre de una columna de origen, se debe actualizar su transformación en el modelo. Las claves de dimensiones son únicas y las cuatro relaciones son de dimensión (uno) a ventas (muchos), con filtro en una sola dirección.

Una cuenta dedicada requiere `CONNECT` en `chinook_dw`, `USAGE` en `public` y `SELECT` en esas cinco tablas. El administrador puede usar `documentacion/acceso_lector.sql`, que no cambia los datos. La contraseña del lector se establece aparte, por ejemplo con `\password chinook_bi_reader` dentro de `psql`.

## Páginas e integrantes

| Página | Responsable | KPIs |
|---|---|---|
| Ingresos | Cristopher Quiros | Crecimiento de ingresos; ingreso por cliente comprador. |
| Clientes | Jeremy Rodriguez | Compradores activos; retención entre meses consecutivos. |
| Catálogo | Brian Rodriguez | Crecimiento de unidades; concentración del género líder. |
| Mercados | Miguel Cruz | Países con ventas; concentración de los cinco artistas principales. |

Los botones laterales navegan entre páginas. En Desktop se activan con **Ctrl + clic**. El filtro de mes afecta las tarjetas y los gráficos del mes. Las líneas tituladas «histórico completo» conservan los 60 meses para dar contexto y permiten comparar periodos, aunque se cambie el mes de análisis. El filtro de país sí afecta esos históricos. Seleccionar categorías en otros gráficos puede cambiar el contexto; hacer clic de nuevo en la selección para retirarla.

La asignación de KPIs se conserva en el documento; las páginas del tablero no muestran nombres de responsables.

Verde y rojo indican evolución favorable o desfavorable frente al periodo anterior según el sentido del indicador; gris indica empate o falta de base. En los indicadores de concentración se considera favorable una reducción de dependencia, sin afirmar que eso aumenta la utilidad. Los KPIs aprobados no incluyen metas numéricas: la marca del Bullet Chart es **el mes previo**, no una meta inventada.

Los importes se muestran en **UM** (unidades monetarias): la fuente no indica un código de moneda ni contiene costos para calcular ganancias. La geografía es la del cliente en el DW, no una reconstrucción histórica de la dirección de facturación.

## Visuales especiales

Se utilizan **Bullet Chart** y **Sankey** de Microsoft, registrados como visuales públicos de AppSource. La primera apertura requiere internet para descargarlos. Si una política del equipo bloquea visuales personalizados, debe habilitarlos el administrador; no sustituirlos silenciosamente por gráficos nativos porque el enunciado exige dos visuales externos.

La página Mercados incluye **Map** y **Decomposition Tree**. Si el mapa está deshabilitado, revisar **Archivo → Opciones y configuración → Opciones → Seguridad → Usar objetos visuales Mapa y Mapa coroplético**. La geocodificación necesita conexión a internet. El árbol se explora con **+**, eligiendo país, género o artista; no representa una jerarquía organizacional fija.

Con varias instancias de Power BI abiertas, verificar esa opción en la ventana del propio proyecto. Si el aviso del mapa continúa, guardar y reabrir el informe después de aplicar el ajuste.

## Comprobar resultados sin modificar la base

Desde la raíz del repositorio, con sus dependencias de Python instaladas:

```powershell
Set-Location D:\chinook_datawarehouse
.\.venv\Scripts\python.exe powerbi\scripts\verificar_dw.py
```

El script lee el DW con una transacción de solo lectura. Genera `validacion/perfil_dw.json` y `validacion/linea_base_mensual.csv` como controles independientes. **Esos archivos no alimentan el informe**. Con el DW original se esperan 2.240 líneas, 412 facturas, 59 compradores, 2.240 unidades y 2.328,60 UM.

En diciembre de 2013, sin filtro de país: ingresos 38,62 UM; crecimiento de ingresos −22,17 %; ingreso por cliente 5,52 UM; 7 compradores; retención 14,29 % (1 de 7); crecimiento de unidades 0 %; concentración del género líder 76,90 %; 5 países; top cinco artistas 89,75 %.

La validación ejecutada contrasta los ocho KPIs en 60 meses: **480 comprobaciones de KPIs y 780 controles en total**, sin diferencias. `validacion/resultado_validacion_dax.json` registra el resultado y `validacion/consulta_mensual.dax` contiene la consulta que se puede ejecutar en la vista de consultas DAX. También se comprobaron meses sin base, retención de cero, variaciones de ambos signos, colores y selección de varios meses; están en `validacion/casos_limite.json`.

Para demostrar una actualización, ejecutar primero el ETL del DW con datos fuente legítimamente actualizados y luego **Inicio → Actualizar** en Power BI. Si la fuente no cambió, los valores deben permanecer iguales. No editar ventas ni inventar filas para simular cambios. Cambiar un filtro demuestra interacción, pero no demuestra actualización de origen.

## Archivos de apoyo

- `documentacion/Proyecto2_Innova.docx` y `.pdf`: metodología, fichas SMART, decisiones y guía de sustentación.
- `documentacion/KPIs_aprobados.docx`: copia intacta del documento entregado por Jeremy.
- `documentacion/medidas_dax.dax`: medidas legibles para estudiar; la definición que abre Power BI está en `Proyecto2_Innova.SemanticModel/definition`.
- `documentacion/catalogo_kpis.json`: nombres, responsables, fórmulas, unidades y ausencia de metas numéricas.
- `scripts/crear_modelo.py` y `scripts/crear_informe.py`: generan las definiciones durante el desarrollo. No se necesitan para abrir o actualizar el tablero y no conviene ejecutarlos después de hacer cambios manuales en Power BI.

Para regenerar únicamente el Word y el PDF se utiliza `scripts/crear_documentacion.py`, que necesita `python-docx` y `reportlab`. No hace falta instalar esas bibliotecas para abrir el informe o leer los documentos terminados.

No compartir `.pbi`, `localSettings.json`, credenciales, archivos temporales ni la carpeta `.system_generated`. Compartir el proyecto completo y que cada integrante configure sus credenciales localmente.
