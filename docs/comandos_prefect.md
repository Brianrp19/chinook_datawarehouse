# Guía Operativa de Ejecución — Prefect, Staging, Data Warehouse y Excel

**Proyecto Universitario:** Chinook Data Platform<br>
**Autores:** Brian y Miguel (Data Warehouse & Analítica) | Jeremy (Staging)<br>
**Fecha de Validación:** 25 de octubre de 2026<br>
**Propósito:** Guía de ejecución cronológica, paso a paso y libre de errores, diseñada para la exposición en vivo del sistema completo.

---

## Índice General
1. [Arquitectura de Terminales y Puertos](#arquitectura-de-terminales-y-puertos)
2. [Paso 1: Comprobar Servicios de PostgreSQL](#paso-1-comprobar-servicios-de-postgresql)
3. [Paso 2: Abrir Repositorio Staging](#paso-2-abrir-repositorio-staging)
4. [Paso 3 (Terminal 1): Encender el Servidor Centralizado Prefect](#paso-3-terminal-1-encender-el-servidor-centralizado-prefect)
5. [Paso 4 (Terminal 2): Ejecutar Pipeline de Staging](#paso-4-terminal-2-ejecutar-pipeline-de-staging)
6. [Paso 5: Abrir Repositorio Chinook Data Warehouse](#paso-5-abrir-repositorio-chinook-data-warehouse)
7. [Paso 6 (Terminal 3): Ejecutar Pipeline del Data Warehouse](#paso-6-terminal-3-ejecutar-pipeline-del-data-warehouse)
8. [Paso 7: Verificación en Dashboard Prefect (Runs vs Deployments)](#paso-7-verificación-en-dashboard-prefect-runs-vs-deployments)
9. [Paso 8: Explotación y Consulta en Microsoft Excel](#paso-8-explotación-y-consulta-en-microsoft-excel)
10. [Los Dos Escenarios de Demostración (A vs B)](#los-dos-escenarios-de-demostración-a-vs-b)
11. [Guía de Solución de Problemas Frecuentes](#guía-de-solución-de-problemas-frecuentes)
12. [Resumen Rápido para la Exposición](#resumen-rápido-para-la-exposición)

---

## Arquitectura de Terminales y Puertos

Para operar el sistema sin interferencias, se utilizan **3 terminales de PowerShell** organizadas por función:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ SERVIDOR CENTRAL (Terminal 1)                                               │
│ Directorio: C:\...\Base de datos\Staging                                    │
│ Función: Servidor Prefect 3 compartiendo base de datos prefect_shared        │
│ Escucha: http://127.0.0.1:4201                                              │
│ Estado: PERMANECE ABIERTA DURANTE TODA LA SESIÓN                            │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
┌──────────────────────────────────────┐  ┌───────────────────────────────────┐
│ STAGING ETL (Terminal 2)             │  │ DATA WAREHOUSE ETL (Terminal 3)   │
│ Directorio: C:\...\Staging           │  │ Directorio: C:\...\datawarehouse  │
│ Puerto BD: 5433 (PostgreSQL 17)      │  │ Puerto BD: 5432 (PostgreSQL 18)   │
│ Base: chinook_staging                │  │ Base: chinook_dw                  │
│ Comandos: .\run.ps1 [-ValidateOnly]  │  │ Comandos: python src/etl_flow.py │
└──────────────────────────────────────┘  └───────────────────────────────────┘
```

---

## Paso 1: Comprobar Servicios de PostgreSQL

* **Proyecto / Carpeta:** Cualquier terminal de PowerShell.
* **Objetivo:** Verificar que ambos motores de PostgreSQL estén activos antes de iniciar los pipelines. *(No es necesario crear bases de datos ni esquemas porque ya están aprovisionados).*

### Comando para Verificar Conectividad de Puertos
```powershell
# Comprobar PostgreSQL 17 (Staging - Puerto 5433)
Test-NetConnection -ComputerName 127.0.0.1 -Port 5433

# Comprobar PostgreSQL 18 (Data Warehouse - Puerto 5432)
Test-NetConnection -ComputerName 127.0.0.1 -Port 5432
```

### Comprobación Opcional de Servicios de Windows
```powershell
Get-Service -Name postgresql*
```

* **Resultado Esperado:** `TcpTestSucceeded : True` en ambos puertos (o servicios en estado `Running`).
* **Qué NO hacer:** No intentar reinstalar servicios ni ejecutar `createdb` si las conexiones responden correctamente.
* **Paso Siguiente:** Pasar al Paso 2 para situarse en Staging.

---

## Paso 2: Abrir Repositorio Staging

* **Proyecto:** Staging (Equipo de Jeremy)
* **Ruta de Trabajo:**
  ```text
  C:\Users\brian\OneDrive\Documentos\Base de datos\Staging
  ```
* **Acción:** Abrir una primera terminal de PowerShell y posicionarse en la carpeta de Staging.

---

## Paso 3 (Terminal 1): Encender el Servidor Centralizado Prefect

* **Proyecto:** Staging
* **Terminal:** **Terminal 1** (Terminal del Servidor)
* **Objetivo:** Iniciar la instancia compartida de Prefect en el puerto `4201` con base persistente en `prefect_shared`.

### 1. Comprobación Previa (¿Ya está encendido?)
Antes de lanzar el servidor, verificar si el puerto 4201 ya está respondiendo para evitar lanzar instancias duplicadas:
```powershell
(Invoke-WebRequest -Uri "http://127.0.0.1:4201/api/health" -UseBasicParsing -TimeoutSec 2).StatusCode
```
- Si devuelve `200`, **el servidor ya está encendido**. ¡NO iniciar otro servidor! Pase directamente al Paso 4.
- Si devuelve error de conexión o tiempo de espera, proceder a encenderlo con los comandos a continuación.

### 2. Comando para Iniciar el Servidor Centralizado
Copiar y ejecutar en la **Terminal 1**:

```powershell
cd "C:\Users\brian\OneDrive\Documentos\Base de datos\Staging"

$env:PREFECT_HOME = "C:\Users\brian\OneDrive\Documentos\Base de datos\prefect_shared"
$env:PREFECT_API_URL = "http://127.0.0.1:4201/api"
$env:PREFECT_UI_API_URL = "http://127.0.0.1:4201/api"
$env:PREFECT_SERVER_ANALYTICS_ENABLED = "false"

.\.venv\Scripts\prefect.exe server start --host 127.0.0.1 --port 4201
```

### 3. Comprobación de Disponibilidad de la API
Esperar unos 10 segundos hasta que la consola muestre el banner de Prefect. Para comprobar la API sin alterar datos, abrir una segunda terminal y ejecutar:
```powershell
(Invoke-WebRequest -Uri "http://127.0.0.1:4201/api/health" -UseBasicParsing).Content
```
* **Resultado Esperado en Terminal 1:**
  ```text
  ___ ___ ___ ___ ___ ___ _____
  | _ \ _ \ __| __| __/ __|_   _|
  |  _/   / _|| _|| _| (__  | |
  |_| |_|_\___|_| |___\___| |_|

  Configure Prefect to communicate with the server with:
      prefect config set PREFECT_API_URL=http://127.0.0.1:4201/api
  View the Dashboard and get started at http://127.0.0.1:4201
  ```
* **Resultado Esperado del Healthcheck:** `{"status":"HEALTHY"}` con código HTTP 200.
* **Manejo de Perfiles vs. Variables de Entorno:**
  Prefect puede emitir una advertencia indicando que el perfil activo difiere de `PREFECT_API_URL`. **Esto es completamente normal:** la variable de sesión `$env:PREFECT_API_URL = "http://127.0.0.1:4201/api"` tiene prioridad directa en PowerShell. Para inspeccionar el perfil sin alterar configuraciones:
  ```powershell
  .\.venv\Scripts\prefect.exe profile inspect
  ```
  *No es necesario ejecutar `prefect profile create` ni modificar perfiles en cada ejecución.*
* **Qué NO hacer:**
  - ⛔ **NO cerrar esta Terminal 1.** Si se cierra, los pipelines no podrán registrar sus tareas.
  - ⛔ **NO ejecutar los ETL** hasta que `/api/health` responda `HEALTHY`.
* **Paso Siguiente:** Dejar la Terminal 1 corriendo y abrir la **Terminal 2**.

---

## Paso 4 (Terminal 2): Ejecutar Pipeline de Staging

* **Proyecto:** Staging
* **Terminal:** **Terminal 2** (Terminal de Ejecución de Staging)
* **Objetivo:** Ejecutar la etapa 1 del sistema (lectura y validación de los 11 archivos CSV y 15.607 registros).

### 1. Inicializar la Terminal 2
```powershell
cd "C:\Users\brian\OneDrive\Documentos\Base de datos\Staging"
$env:PREFECT_API_URL = "http://127.0.0.1:4201/api"
```

### 2. Seleccionar UNA de las Dos Alternativas de Ejecución

#### 🟢 OPCIÓN A: Modo Práctica / Auditoría Segura (RECOMENDADO PARA DEMOSTRACIÓN)
Valida la integridad de los 11 archivos CSV y los 15.607 registros contra la base de datos sin alterar los datos existentes:
```powershell
.\run.ps1 -ValidateOnly
```
* **Tareas Prefect ejecutadas:** 2 tareas.
* **Resultado esperado:** Validación exitosa de los 11 CSVs, 15.607 filas coincidentes y estado `Completed`.

#### 🔵 OPCIÓN B: Modo Carga Completa (Full Refresh)
Extrae los 11 CSVs, vacía transaccionalmente las 11 tablas `stg_*`, carga los registros originales y realiza la conciliación:
```powershell
.\run.ps1
```
* **Tareas Prefect ejecutadas:** 3 tareas (Extracción, Carga atómica, Validación).
* **Resultado esperado:** Carga de 15.607 registros en PostgreSQL 17 y estado `Completed`.

> 💡 **Nota de Procedimiento:** Las opciones A y B son **alternativas mutuamente excluyentes**. Para una exposición fluida o pruebas previas, utilice la **Opción A (`-ValidateOnly`)**.

### 3. Comprobación Opcional del Usuario Lector
Para comprobar que el usuario de solo lectura del Data Warehouse (`chinook_stg_reader`) tiene los permisos adecuados según contrato:
```powershell
.\.venv\Scripts\python.exe scripts/staging_contract.py --check --env-file .env.reader
```
*(Es una comprobación de seguridad adicional; no es requisito obligatorio en cada corrida).*

* **Paso Siguiente:** Confirmar que en Prefect aparece `Completed` y pasar al Paso 5.

---

## Paso 5: Abrir Repositorio Chinook Data Warehouse

* **Proyecto:** Chinook Data Warehouse (Brian y Miguel)
* **Ruta de Trabajo:**
  ```text
  C:\Users\brian\OneDrive\Documentos\Base de datos\chinook_datawarehouse
  ```
* **Acción:** Mantener abierto el servidor Prefect de la Terminal 1 y abrir una tercera terminal (**Terminal 3**) en este directorio.

---

## Paso 6 (Terminal 3): Ejecutar Pipeline del Data Warehouse

* **Proyecto:** `chinook_datawarehouse`
* **Terminal:** **Terminal 3** (Terminal de Ejecución del Data Warehouse)
* **Objetivo:** Ejecutar la etapa 2: extracción segura desde Staging (PostgreSQL 17), validaciones de negocio, transformaciones dimensionales y carga en PostgreSQL 18 (`chinook_dw`).

### 1. Inicializar la Terminal 3
```powershell
cd "C:\Users\brian\OneDrive\Documentos\Base de datos\chinook_datawarehouse"
$env:PREFECT_API_URL = "http://127.0.0.1:4201/api"
```

### 2. Seleccionar UNA de las Dos Alternativas de Ejecución

#### 🟢 OPCIÓN A: Modo Auditoría en Memoria (RECOMENDADO PARA DEMOSTRACIÓN SEGURA)
Ejecuta la extracción real desde PostgreSQL 17 bajo aislamiento `REPEATABLE READ READ ONLY`, aplica todas las reglas de validación y transforma las 4 dimensiones y la tabla de hechos en memoria, **sin escribir en PostgreSQL 18**:
```powershell
.\.venv\Scripts\python.exe src/etl_flow.py --no-load
```
* **Tareas Prefect registradas (4 tareas):**
  1. `task_extraer_staging` (11 tablas, 15.607 registros)
  2. `task_validar_integridad` (0 claves huérfanas)
  3. `task_validar_calidad_negocio` (precios y montos cuadrados)
  4. `task_transformar` (dimensiones generadas en memoria)
* **Resultado en consola:** `[MODO AUDITORIA/SIN CARGA]: Extracción, validación y transformación completadas en memoria. No se realizaron escrituras en PostgreSQL 18 chinook_dw.`

#### 🔵 OPCIÓN B: Modo Carga Completa del Data Warehouse
Realiza el flujo completo de punta a punta: extracción, validaciones previas, transformación dimensional, vaciado limpio con `TRUNCATE CASCADE`, carga en PostgreSQL 18 y conciliación matemática obligatoria:
```powershell
.\.venv\Scripts\python.exe src/etl_flow.py --run-once
```
* **Tareas Prefect registradas (6 tareas):**
  1. `task_extraer_staging`
  2. `task_validar_integridad`
  3. `task_validar_calidad_negocio`
  4. `task_transformar`
  5. `task_cargar` (Carga transaccional en `chinook_dw`)
  6. `task_validar` (Conciliación en base de datos)
* **Resultado en consola:**
  ```text
  CONTROL DE CALIDAD Y CUADRATURA DEL DATA WAREHOUSE
    * dim_date        :   1.826 filas
    * dim_employee    :       8 filas
    * dim_customer    :      59 filas
    * dim_track       :   3.503 filas
    * fact_sales      :   2.240 filas
    * total fact_sales: $2.328,60
    * inconsistencias : 0
  >>> VALIDACIÓN EXITOSA: El Data Warehouse quedó 100% consistente y cuadrado.
  ```

### 3. Modo Despliegue / Servicio (`--serve` - Solo Referencia Avanzada)
```powershell
# Solo para registrar el flujo persistente como servicio en Prefect (Opcional)
.\.venv\Scripts\python.exe src/etl_flow.py --serve
```
*Este modo mantiene un agente en espera en la terminal para recibir disparos remotos. No es parte del procedimiento operativo principal de la exposición.*

> ⚠️ **Qué NO hacer:**
> - ⛔ **NO presionar el botón "Run Python File" (Play) del editor.** Si se ejecuta sin argumentos, el script muestra el menú de ayuda y no procesa el flujo.
> - ⛔ **NO ejecutar `--no-load` y `--run-once` de forma simultánea.** Elija una sola opción.
* **Paso Siguiente:** Pasar al Paso 7 para verificar el estado en el navegador.

---

## Paso 7: Verificación en Dashboard Prefect (Runs vs Deployments)

* **URL de Acceso:** [http://127.0.0.1:4201](http://127.0.0.1:4201)
* **Pestaña Principal:** **Runs**

### 1. Verificación de Flujos en la Pestaña "Runs"
En la sección **Runs**, deben visualizarse las ejecuciones realizadas desde las terminales de PowerShell:
- **`Chinook Staging ETL`** → Estado: `Completed` (Verde).
- **`Chinook ETL Data Warehouse`** → Estado: `Completed` (Verde).

### 2. Evidencia Histórica Real Auditada (25 de octubre de 2026)
Como registro comprobado durante las pruebas oficiales de integración:
* **Staging:**
  - `valiant-pegasus` — **Completed** — 2 tareas (`run.ps1 -ValidateOnly`).
* **Data Warehouse:**
  - `lovely-toucan` — **Completed** — 4 tareas (`src/etl_flow.py --no-load`).
  - `inventive-husky` — **Completed** — 6 tareas (`src/etl_flow.py --run-once`).

*(Nota: Los nombres aleatorios como `valiant-pegasus` o `inventive-husky` son generados automáticamente por Prefect en cada ejecución; lo fundamental es verificar el estado `Completed`).*

---

### 3. Diferencia Crucial: RUNS vs DEPLOYMENTS

Es fundamental comprender esta distinción conceptual para evitar confusiones en la presentación:

| Concepto | Qué Es | Para Qué Sirve en Nuestro Proyecto | Estado Típico Esperado |
|---|---|---|---|
| **Runs** | Historial de ejecuciones reales disparadas desde PowerShell. | **Es nuestra herramienta oficial de verificación.** Muestra los logs, tiempos y tareas completadas con éxito. | **Completed** ✅ |
| **Deployments** | Definiciones de despliegue persistente registradas en el servidor. | Permite encolar ejecuciones futuras desde la interfaz gráfica o programaciones automáticas. | `chinook-local` (**Not Ready**) ⚠️ |

#### ¿Por qué aparece un Deployment como "Not Ready" o una ejecución como "Late"?
- En Prefect, registramos un deployment llamado `chinook-local`.
- Si el proceso persistente (`src/etl_flow.py --serve`) no está ejecutándose en segundo plano, el deployment muestra **Not Ready**, lo cual significa simplemente: *"No hay un agente escuchando activamente en este momento"*.
- Si previamente se disparó una ejecución desde la interfaz web (por ejemplo, la ejecución histórica `origami-avocet`), aparecerá en estado **Late** y sin logs porque no hubo ningún proceso worker para atenderla.
- 🎯 **Conclusión:** Que un Deployment esté *Not Ready* o tenga una ejecución *Late* **NO AFECTA EN ABSOLUTO** a las ejecuciones manuales de PowerShell (`inventive-husky`, `lovely-toucan`), las cuales se completaron de manera 100% exitosa.
- **Nuestro procedimiento oficial se basa en PowerShell + Runs**, sin depender de Deployments ni Quick Run.

---

## Paso 8: Explotación y Consulta en Microsoft Excel

* **Proyecto:** `chinook_datawarehouse`
* **Archivo Principal:** [`excel/Chinook_Analisis_DataWarehouse.xlsx`](../excel/Chinook_Analisis_DataWarehouse.xlsx)
* *(Nota: El archivo `docs/historico/Book1.xlsx` se conserva exclusivamente como respaldo histórico original).*

### 1. Abrir el Libro de Análisis
Desde la raíz de `chinook_datawarehouse` en PowerShell:
```powershell
Start-Process ".\excel\Chinook_Analisis_DataWarehouse.xlsx"
```

### 2. Arquitectura de Conexión en Excel
- **Motor:** **Power Query** conectado mediante TCP a PostgreSQL 18 (`127.0.0.1:5432`, base `chinook_dw`).
- **Consultas Integradas:** Excel consume de forma individual las 5 tablas del modelo dimensional en estrella:
  1. `dim_date` (1.826 registros)
  2. `dim_customer` (59 registros)
  3. `dim_employee` (8 registros)
  4. `dim_track` (3.503 registros)
  5. `fact_sales` (2.240 registros, $2.328,60)

### 3. Actualización de Datos
1. En Microsoft Excel, situarse en la cinta superior.
2. Hacer clic en **Datos → Actualizar todo** (*Refresh All*).
3. Power Query reejecutará las consultas contra PostgreSQL 18 y actualizará automáticamente todas las tablas dinámicas, segmentadores y gráficos de KPI.
4. **No es necesario volver a ejecutar los scripts de Python** para actualizar Excel; la conexión es directa a la base de datos.

### 4. Resultados de Negocio Cuadrados
* **Total de Ventas Global:** **$2.328,60**
* **Total de Transacciones:** **2.240 líneas de factura**
* *(Nota: Asegurarse de que los segmentadores de año o país tengan seleccionado "(Todo)" para apreciar el total consolidado).*

---

## Los Dos Escenarios de Demostración (A vs B)

Para evitar mezclar comandos de carga con comandos de validación, elija claramente el escenario según el propósito:

### 🟢 ESCENARIO A — VALIDACIÓN SEGURA (Práctica / Exposición sin Modificar BD)
*Garantiza una demostración 100% libre de riesgos sin realizar escrituras ni modificaciones en las bases de datos.*

1. **Verificar Servicios:** Confirmar que PostgreSQL 17 (5433) y 18 (5432) estén activos.
2. **Terminal 1:** Iniciar servidor Prefect si está apagado (`.\.venv\Scripts\prefect.exe server start --host 127.0.0.1 --port 4201`).
3. **Terminal 2 (Staging):**
   ```powershell
   cd "C:\Users\brian\OneDrive\Documentos\Base de datos\Staging"
   $env:PREFECT_API_URL = "http://127.0.0.1:4201/api"
   .\run.ps1 -ValidateOnly
   ```
4. **Terminal 3 (Data Warehouse):**
   ```powershell
   cd "C:\Users\brian\OneDrive\Documentos\Base de datos\chinook_datawarehouse"
   $env:PREFECT_API_URL = "http://127.0.0.1:4201/api"
   .\.venv\Scripts\python.exe src/etl_flow.py --no-load
   ```
5. **Navegador:** Abrir `http://127.0.0.1:4201` → Revisar **Runs** → Confirmar ambos flujos en `Completed`.
6. **Excel:** Abrir `Chinook_Analisis_DataWarehouse.xlsx` y mostrar los KPIs.

---

### 🔵 ESCENARIO B — EJECUCIÓN COMPLETA (Carga Real y Conciliación Matemática)
*Ejecuta la recarga atómica transaccional de Staging y del Data Warehouse.*

1. **Verificar Servicios:** Confirmar que PostgreSQL 17 (5433) y 18 (5432) estén activos.
2. **Terminal 1:** Iniciar servidor Prefect si está apagado.
3. **Terminal 2 (Staging):**
   ```powershell
   cd "C:\Users\brian\OneDrive\Documentos\Base de datos\Staging"
   $env:PREFECT_API_URL = "http://127.0.0.1:4201/api"
   .\run.ps1
   ```
   *Esperar mensaje de carga completada exitosamente.*
4. **Terminal 3 (Data Warehouse):**
   ```powershell
   cd "C:\Users\brian\OneDrive\Documentos\Base de datos\chinook_datawarehouse"
   $env:PREFECT_API_URL = "http://127.0.0.1:4201/api"
   .\.venv\Scripts\python.exe src/etl_flow.py --run-once
   ```
   *Esperar mensaje: `El Data Warehouse está cuadrado y consistente con la fuente original.`*
5. **Navegador:** Abrir `http://127.0.0.1:4201` → Revisar **Runs** → Confirmar 6 tareas completadas.
6. **Excel:** Abrir `Chinook_Analisis_DataWarehouse.xlsx` → Pulsar **Datos → Actualizar todo**.

---

## Guía de Solución de Problemas Frecuentes

### 1. Error: `WinError 10061: No se puede establecer una conexión ya que el equipo de destino denegó expresamente dicha conexión`
* **Causa:** El servidor de Prefect en el puerto 4201 no está iniciado o fue cerrado.
* **Solución:**
  1. Ir a la **Terminal 1**.
  2. Ejecutar el comando del Paso 3 para iniciar el servidor Prefect en el puerto 4201.
  3. Esperar a que la comprobación `(Invoke-WebRequest -Uri "http://127.0.0.1:4201/api/health").StatusCode` responda `200` antes de volver a lanzar el ETL.

### 2. Error: `Puerto 4201 ya está en uso` / Conflicto al iniciar servidor
* **Causa:** Ya existía una instancia de Prefect ejecutándose en segundo plano.
* **Solución:**
  1. Verificar si responde: `Invoke-WebRequest http://127.0.0.1:4201/api/health`.
  2. Si responde `200`, **reutilice ese servidor**. No necesita abrir otro.
  3. Si el puerto quedó tomado por un proceso colgado y desea reiniciarlo:
     ```powershell
     Get-NetTCPConnection -LocalPort 4201 | Select-Object OwningProcess
     Stop-Process -Id <NUMERO_PID> -Force
     ```

### 3. Conflicto entre Perfil Prefect y `PREFECT_API_URL`
* **Síntoma:** Advertencia en consola: `Profile '...' has a different API URL than environment variable...`
* **Solución:** La variable de sesión `$env:PREFECT_API_URL = "http://127.0.0.1:4201/api"` tiene precedencia sobre cualquier perfil local. La advertencia es informativa y no impide la ejecución. Para alinear el perfil definitivamente sin crear perfiles nuevos:
  ```powershell
  .\.venv\Scripts\prefect.exe config set PREFECT_API_URL="http://127.0.0.1:4201/api"
  ```

### 4. La Terminal del Servidor se cerró accidentalmente
* **Solución:**
  1. Abrir una nueva terminal.
  2. Ejecutar los comandos de la **Terminal 1** (Paso 3).
  3. Esperar 10 segundos y reanudar las ejecuciones de los ETL. No se pierden datos históricos ya registrados en `prefect_shared`.

### 5. Se ejecutó `etl_flow.py` sin argumentos (o botón Play de VS Code / Antigravity)
* **Síntoma:** El script termina en 1 segundo imprimiendo: `Especifique una opción: --run-once (ejecución única), --no-load (modo auditoría) o --serve (servidor)`.
* **Solución:** Invocar el comando desde PowerShell incluyendo explícitamente el parámetro:
  - Práctica: `.\.venv\Scripts\python.exe src/etl_flow.py --no-load`
  - Carga: `.\.venv\Scripts\python.exe src/etl_flow.py --run-once`

### 6. Deployment muestra "Not Ready" o una ejecución aparece "Late"
* **Causa:** Es el comportamiento esperado cuando el servidor no tiene un agente persistente escuchando.
* **Solución:** No es un error. Las ejecuciones oficiales del proyecto se ejecutan de forma interactiva y se consultan en la pestaña **Runs**. No intente lanzar "Quick Run" desde Deployments.

### 7. Excel no actualiza o muestra error de conexión
* **Causa:** PostgreSQL 18 no está corriendo en el puerto 5432 o las credenciales locales de Windows no están autenticadas en Power Query.
* **Solución:**
  1. Verificar puerto con `Test-NetConnection -ComputerName 127.0.0.1 -Port 5432`.
  2. En Excel: **Datos → Obtener datos → Configuración del origen de datos** → Confirmar que el usuario sea `postgres` y el puerto `5432`.

---

## Resumen Rápido para la Exposición

### 🖥️ BLOQUE DE TERMINALES (Copiar y Pegar)

#### TERMINAL 1 (Servidor Prefect — Iniciar primero y mantener abierta)
```powershell
cd "C:\Users\brian\OneDrive\Documentos\Base de datos\Staging"
$env:PREFECT_HOME = "C:\Users\brian\OneDrive\Documentos\Base de datos\prefect_shared"
$env:PREFECT_API_URL = "http://127.0.0.1:4201/api"
$env:PREFECT_UI_API_URL = "http://127.0.0.1:4201/api"
$env:PREFECT_SERVER_ANALYTICS_ENABLED = "false"
.\.venv\Scripts\prefect.exe server start --host 127.0.0.1 --port 4201
```

---

#### TERMINAL 2 (Staging ETL)
```powershell
cd "C:\Users\brian\OneDrive\Documentos\Base de datos\Staging"
$env:PREFECT_API_URL = "http://127.0.0.1:4201/api"

# Opción Práctica (Sin recargar tablas):
.\run.ps1 -ValidateOnly

# Opción Carga Completa (Full Refresh):
# .\run.ps1
```

---

#### TERMINAL 3 (Chinook Data Warehouse ETL)
```powershell
cd "C:\Users\brian\OneDrive\Documentos\Base de datos\chinook_datawarehouse"
$env:PREFECT_API_URL = "http://127.0.0.1:4201/api"

# Opción Práctica (Auditoría en memoria, sin escribir en DW):
.\.venv\Scripts\python.exe src/etl_flow.py --no-load

# Opción Carga Completa (Escribe en PostgreSQL 18 y concilia):
# .\.venv\Scripts\python.exe src/etl_flow.py --run-once
```

---

#### MONITOREO & EXCEL
```powershell
# 1. Monitoreo Web:
Start-Process "http://127.0.0.1:4201"

# 2. Abrir Excel Analítico:
cd "C:\Users\brian\OneDrive\Documentos\Base de datos\chinook_datawarehouse"
Start-Process ".\excel\Chinook_Analisis_DataWarehouse.xlsx"
```
*(En Excel: pulsar **Datos → Actualizar todo**).*
