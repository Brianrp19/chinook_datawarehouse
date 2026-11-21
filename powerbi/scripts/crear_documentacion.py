"""Genera el documento editable y su PDF a partir del catálogo y la validación real."""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "documentacion"
INK, TEAL, PALE = "16324F", "008F98", "EFF4F8"
KPI = json.loads((OUT / "catalogo_kpis.json").read_text(encoding="utf-8"))
PROFILE = json.loads((ROOT / "validacion/perfil_dw.json").read_text(encoding="utf-8"))
VALID = json.loads((ROOT / "validacion/resultado_validacion_dax.json").read_text(encoding="utf-8"))
with (ROOT / "validacion/linea_base_mensual.csv").open(encoding="utf-8-sig", newline="") as f:
    MONTHS = list(csv.DictReader(f))
LAST = MONTHS[-1]

BLOCKS = []


def h(text, level=1):
    BLOCKS.append(("h", text, level))


def p(text):
    BLOCKS.append(("p", text))


def table(headers, rows):
    BLOCKS.append(("table", [headers] + [list(row) for row in rows]))


def code(text):
    BLOCKS.append(("code", text.strip()))


def page():
    BLOCKS.append(("page",))


def content():
    h("GRUPO INNOVA S.A.")
    h("Tablero gerencial de Chinook", 2)
    p("Proyecto 2 · Continuación del Data Warehouse del Proyecto 1")
    p("Universidad Técnica Nacional · ISW-911 · Minería de Datos · III cuatrimestre de 2026")
    p("Equipo: Brian Rodriguez, Cristopher Quiros, Jeremy Rodriguez y Miguel Cruz.")
    p("Herramientas: PostgreSQL, Prefect del Proyecto 1 y Microsoft Power BI Desktop.")
    p("Fuente: chinook_dw · Datos históricos: enero de 2009 a diciembre de 2013.")
    p("Versión de trabajo: 20 de noviembre de 2026. Las definiciones se basan en KPIs.docx, cuya aprobación fue confirmada por Jeremy. No se atribuyen al profesor metas numéricas que el documento no contiene.")
    page()
    h("1. Propósito y continuidad con el Proyecto 1")
    p("El tablero permite revisar ingresos, comportamiento de compradores, volumen de ventas y concentración comercial. Sus ocho indicadores se calculan desde el Data Warehouse que ya construyó el equipo. Power BI agrega la capa de análisis; no reemplaza la preparación de datos ni vuelve a ejecutar el ETL.")
    table(["Etapa", "Propósito", "Resultado"], [
        ["Origen", "Conservar los archivos originales de Chinook.", "11 CSV del Proyecto 1."],
        ["Staging / PostgreSQL 17", "Recibir y comprobar la carga de origen.", "chinook_staging, puerto local 5433."],
        ["DW / PostgreSQL 18", "Transformar y organizar ventas en un modelo estrella.", "chinook_dw, puerto local 5432."],
        ["Power BI", "Importar el DW, calcular DAX y visualizar los KPIs.", "Cuatro páginas interactivas."],
    ])
    p("Flujo de actualización: datos de origen → ejecución independiente del ETL de Staging → ejecución independiente del ETL del DW → Inicio / Actualizar en Power BI. Si el DW ya está cargado, basta con conectarse a él para construir este proyecto.")
    h("Modelo estrella y granularidad", 2)
    p("Ventas contiene una fila por línea de factura. Fecha, Clientes, Canciones y Empleados describen cuándo ocurrió la venta, quién compró, qué contenido se vendió y qué empleado de soporte tiene asignado el cliente. Las cuatro dimensiones filtran Ventas con relaciones de uno a muchos y una sola dirección. Esta organización facilita agregar importes sin repetir los atributos descriptivos en cada cálculo (Microsoft, s. f.-a).")
    table(["PostgreSQL", "Power BI", "Clave de relación"], [
        ["fact_sales", "Ventas", "sales_key; claves de las cuatro dimensiones"],
        ["dim_date", "Fecha", "date_key → Clave fecha"],
        ["dim_customer", "Clientes", "customer_key → Clave cliente"],
        ["dim_track", "Canciones", "track_key → Clave canción"],
        ["dim_employee", "Empleados", "employee_key → Clave empleado"],
    ])
    p("El calendario contiene 1.826 días. La última venta es del 22/12/2013, aunque el calendario termina el 31/12/2013. Hay 2.240 líneas, 412 facturas, 59 compradores, 2.240 unidades y 2.328,60 unidades monetarias (UM). Estos son controles del conjunto histórico, no metas comerciales.")
    page()
    h("2. Metodología para diseñar y construir KPIs")
    p("Se usa una secuencia de objetivo → pregunta de gestión → indicador → contrato de cálculo → visualización → comprobación → decisión. El Balanced Scorecard vincula objetivos estratégicos con medidas y su seguimiento; aquí se toma esa relación como marco de referencia y se limita el alcance a las preguntas comerciales que el DW puede responder. No se afirma haber implementado un cuadro de mando integral completo (Balanced Scorecard Institute, s. f.).")
    table(["Paso", "Aplicación en este proyecto"], [
        ["1. Definir el objetivo", "Observar evolución de ventas, relación con compradores y diversificación."],
        ["2. Formular la pregunta", "Ejemplo: ¿qué proporción de los compradores del mes pasado volvió este mes?"],
        ["3. Fijar el contrato", "Fórmula, grano mensual, universo de clientes, denominador, filtros y casos sin base."],
        ["4. Asignar responsabilidades", "Dos KPIs por integrante, de acuerdo con el documento aprobado."],
        ["5. Revisar SMART", "Especificidad, medición, viabilidad, relevancia y periodo explícitos."],
        ["6. Construir y contextualizar", "Medidas DAX, gráficos del mes e históricos; referencias claramente identificadas."],
        ["7. Contrastar", "Comparar el motor DAX con un cálculo independiente desde PostgreSQL."],
        ["8. Actuar y revisar", "Investigar cambios y proponer acciones; medir su efecto sin confundir asociación con causalidad."],
    ])
    p("SMART ayuda a precisar lo que se desea lograr y cómo comprobarlo: específico, medible, alcanzable, relevante y delimitado en el tiempo (Centers for Disease Control and Prevention, s. f.). Las fichas siguientes aplican esos criterios al alcance y a la medición de cada KPI.")
    h("Metas y referencias", 2)
    p("El documento aprobado plantea definir las metas a partir de la línea base y no contiene umbrales numéricos aprobados. Por esa razón, las tarjetas comparan contra el mes calendario anterior. Una referencia histórica no constituye una meta. Para cerrar objetivos comerciales SMART con umbrales de cumplimiento, gerencia y profesor deben fijar y validar después una meta, su plazo y la capacidad de alcanzarla. Esa decisión no se inventa en este entregable.")
    p("Los colores indican evolución relativa: verde para una variación favorable, rojo para una desfavorable y gris para empate o ausencia de base. En concentración se considera favorable reducir dependencia; eso no prueba por sí solo mayor rentabilidad.")
    for index, k in enumerate(KPI):
        page()
        ident = k["id"]
        h(f"3.{index+1}. {ident} · {k['nombre']}")
        p(f"Responsable: {k['responsable']} · Frecuencia: mensual · Unidad: {k['unidad']}.")
        questions = ["¿Los ingresos aumentaron o disminuyeron frente al mes anterior?", "¿Cuánto ingreso genera, en promedio, cada cliente que compró?", "¿Cuántas personas distintas compraron durante el mes?", "¿Qué proporción de los compradores del mes anterior regresó?", "¿Aumentó o disminuyó el volumen vendido frente al mes anterior?", "¿Qué proporción del ingreso depende del género líder?", "¿En cuántos países hubo clientes compradores durante el mes?", "¿Cuánto ingreso depende de los cinco artistas líderes del periodo?"]
        purposes = ["Detectar cambios de ingreso para investigar campañas, catálogo y comportamiento de compra.", "Analizar el valor medio de la relación con compradores y oportunidades de venta complementaria.", "Seguir el tamaño de la base de compradores sin confundir clientes registrados con clientes activos.", "Observar continuidad de compra y orientar análisis de fidelización.", "Separar cambios de volumen de posibles cambios en la mezcla de precios.", "Reconocer dependencia de una categoría y estudiar diversificación del catálogo.", "Vigilar el alcance geográfico real de las ventas.", "Identificar dependencia de pocos artistas y riesgo de concentración comercial."]
        p("Pregunta de gestión: " + questions[index])
        p("Justificación: " + purposes[index])
        table(["Atributo SMART", "Aplicación"], [
            ["S · Específico", k["definicion"]],
            ["M · Medible", "Fórmula DAX reproducible, fuente identificada y unidad definida. Se contrasta por mes contra el DW."],
            ["A · Alcanzable", "La medición es viable con los datos disponibles. La viabilidad de una meta comercial queda pendiente de fijar su umbral y recursos."],
            ["R · Relevante", purposes[index]],
            ["T · Temporal", "Un mes calendario seleccionado; cuando corresponde, se compara con el mes inmediatamente anterior."],
        ])
        h("Implementación DAX", 2)
        code(k["dax"])
        if index == 3:
            p("El numerador usa INTERSECT entre dos conjuntos de claves de compradores. COALESCE convierte el conteo vacío en cero cuando sí existe un mes anterior con compradores. Sin base previa, la medida permanece vacía. En diciembre de 2013 regresó 1 de los 7 compradores de noviembre: 14,29 %.")
        elif index == 7:
            p("TOPN ordena por ingreso descendente y por identificador de artista ascendente. El segundo criterio resuelve empates y evita incorporar más de cinco artistas por igualdad de ingresos. Si solo compraron contenidos de menos de cinco artistas, utiliza los disponibles.")
        elif index == 1:
            p("El denominador cuenta compradores del mes, no los 59 clientes de la dimensión. CONVERT a DOUBLE conserva precisión al dividir importes monetarios entre cantidades; el formato presenta dos decimales.")
        elif index == 5:
            p("Se calcula la participación del género con más ingresos; no es un índice HHI ni una suma del top 3. El catálogo Chinook también contiene géneros de video, que se conservan porque las definiciones aprobadas no ordenan excluirlos.")
        elif index == 6:
            p("No basta contar países de Clientes: se incluyen solamente los que tienen ventas en el contexto. El país corresponde al cliente actual del DW, no necesariamente a la dirección histórica de facturación.")
        elif index in [0, 4]:
            p("DIVIDE evita dividir por cero. El primer mes no tiene comparación dentro del conjunto de datos y se presenta como Sin base, no como crecimiento de 0 %. Un resultado negativo significa descenso frente al periodo previo.")
        else:
            p("DISTINCTCOUNT se aplica sobre claves de compradores en Ventas. Varias líneas o facturas del mismo cliente no incrementan artificialmente el número de compradores.")
    page()
    h("4. DAX: cómo funciona el contexto")
    p("Una medida no guarda un resultado fijo por fila: se evalúa según los filtros de la visualización. Al seleccionar diciembre de 2013, Fecha filtra las líneas de Ventas correspondientes a ese mes. Un filtro de país reduce además el conjunto de compradores y ventas. Las medidas se recalculan sobre ese contexto.")
    table(["Función o recurso", "Uso concreto"], [
        ["SUM", "Sumar importes y cantidades de las líneas de factura."],
        ["DISTINCTCOUNT", "Contar compradores y facturas sin duplicarlos por sus líneas."],
        ["CALCULATE", "Evaluar una medida cambiando el contexto de fechas o categorías."],
        ["PREVIOUSMONTH", "Obtener las fechas del mes calendario anterior."],
        ["REMOVEFILTERS", "Quitar el mes actual antes de aplicar las fechas del anterior."],
        ["VAR / RETURN", "Nombrar resultados intermedios y expresar el cálculo por pasos."],
        ["DIVIDE", "Manejar divisiones sin denominador válido."],
        ["VALUES / INTERSECT", "Construir conjuntos de compradores y encontrar los que están en ambos meses."],
        ["COALESCE", "Mostrar cero retenidos cuando la intersección está vacía pero existe base previa."],
        ["ADDCOLUMNS / FILTER", "Calcular ingresos por categoría y conservar las categorías pertinentes."],
        ["TOPN / SUMX / MAXX", "Obtener cinco artistas, sumar sus ingresos y encontrar el género líder."],
        ["HASONEVALUE / SWITCH", "Exigir un mes y escoger el color según el resultado de la comparación."],
    ])
    p("Los KPIs mensuales requieren un único mes. Si se seleccionan varios meses, no se presenta un porcentaje mensual ambiguo. En los históricos, cada punto tiene su propio mes y por eso puede evaluarse correctamente. Los históricos ignoran la selección del segmentador de mes, pero conservan el filtro de país.")
    h("Medida auxiliar de retención", 2)
    import runpy
    measures = runpy.run_path(str(ROOT / "scripts/crear_modelo.py"), run_name="modelo_documental")["MEASURES"]
    code(next(m["expression"] for _, m in measures if m["name"] == "Clientes retenidos"))
    page()
    h("5. Diseño del tablero y elección de visualizaciones")
    table(["Página", "KPIs y contexto", "Razón de diseño"], [
        ["Ingresos", "Dos tarjetas, línea mensual y barras por país.", "Distinguir evolución, valor por comprador y origen geográfico del ingreso."],
        ["Clientes", "Dos tarjetas, Bullet Chart, retenidos e histórico de retención.", "Mostrar actividad y continuidad; la marca del Bullet es el mes previo, no una meta."],
        ["Catálogo", "Dos tarjetas, histórico de unidades y Sankey país → género.", "Contextualizar volumen y dependencia del género líder con la mezcla de compras."],
        ["Mercados", "Dos tarjetas, Map y Decomposition Tree.", "Ubicar mercados y explorar cómo se distribuyen los ingresos por país, género y artista."],
    ])
    p("La navegación lateral mantiene cuatro áreas de análisis. Las tarjetas usan jerarquía tipográfica clara; los históricos emplean un eje temporal continuo para incluir todos los meses. La paleta utiliza azul para estructura, turquesa para datos y verde/rojo para evolución. Los nombres de responsables no se muestran en el tablero por preferencia de Jeremy; la asignación individual permanece en las fichas de este documento.")
    p("Bullet Chart y Sankey son visuales no nativos de Microsoft publicados en AppSource. Se documenta su procedencia y se requieren internet y permiso local para cargarlos. El árbol y el mapa son visuales nativos. El mapa clásico puede generar una advertencia de obsolescencia en versiones recientes de Power BI; se conserva para cumplir el visual Map solicitado en el enunciado.")
    p("Para explorar el árbol, pulsar + junto al nodo y elegir País, Género o Artista. Una rama representa una segmentación del ingreso, no una afirmación causal. El mapa usa la categoría geográfica Country de Clientes[País]. Su ubicación depende de la geocodificación del proveedor de mapas.")
    page()
    h("6. Validación y casos que cambian la interpretación")
    p(f"Se contrastaron los ocho KPIs en {VALID['meses']} meses: {VALID['comparaciones_kpi']} comparaciones de KPIs y {VALID['comparaciones_totales']} controles numéricos en total. El cálculo independiente consulta PostgreSQL en solo lectura y utiliza importes en centavos antes de agregarlos. La comparación con el motor DAX exige la misma presencia de vacíos y una tolerancia numérica relativa y absoluta de 1e-10. Resultado registrado: {len(VALID['errores'])} diferencias.")
    table(["Control de diciembre de 2013", "Resultado"], [
        ["Ingresos del mes", "38,62 UM; noviembre: 49,62 UM"],
        ["KPI 01 · Crecimiento de ingresos", "−22,17 %"],
        ["KPI 02 · Ingreso por comprador", "5,52 UM/cliente"],
        ["KPI 03 · Compradores activos", "7"],
        ["KPI 04 · Retención", "14,29 %; regresó 1 de 7"],
        ["KPI 05 · Crecimiento de unidades", "0 %; 38 unidades en ambos meses"],
        ["KPI 06 · Concentración del género líder", "76,90 %"],
        ["KPI 07 · Países con ventas", "5"],
        ["KPI 08 · Concentración de cinco artistas", "89,75 %"],
    ])
    p("Casos revisados: primer mes sin base; meses con cero compradores retenidos; denominador inexistente; variaciones positivas, negativas e iguales; distinción entre facturas y líneas; y empates del top cinco. La salida completa se conserva en validacion/resultado_validacion_dax.json y la consulta reproducible en validacion/consulta_mensual.dax.")
    h("Límites de lo que se puede concluir", 2)
    p("Los datos son históricos y de demostración. La fuente no identifica moneda ni incluye costos: se utiliza UM y no se calculan ganancias. El DW usa atributos actuales de clientes; no reconstruye países históricos. El empleado de soporte asignado no se interpreta como autor probado de cada venta. Un KPI no demuestra que una campaña o decisión causó el cambio observado.")
    page()
    h("7. Abrir, compartir y demostrar una actualización")
    p("Abrir Proyecto2_Innova.pbip junto con sus carpetas .Report y .SemanticModel. La conexión usa los parámetros Servidor = localhost:5432 y BaseDatos = chinook_dw. Cada integrante introduce sus credenciales PostgreSQL en Power BI; el .env de Python no configura esta autenticación. El DW debe estar cargado previamente según el Proyecto 1.")
    p("Si Power BI solicita autenticación, seleccionar Database y una cuenta con SELECT sobre las cinco tablas. Si se utiliza el servidor local sin TLS de esta práctica, puede aparecer Encryption Support; continuar con OK para ese origen local. Un servidor remoto debe contar con su configuración de seguridad correspondiente. Si se repite el formulario de credenciales, probar el conector PostgreSQL en un informe vacío permite distinguir un problema de autenticación de uno del informe.")
    p("Power BI usa Importación: Actualizar vuelve a consultar el DW. Los segmentadores consultan la copia importada y no ejecutan el ETL. En una computadora distinta, localhost apunta a esa computadora; se requiere su DW local o la dirección del servidor compartido. Compartir el informe no copia el servicio PostgreSQL ni sus credenciales (Microsoft, s. f.-b).")
    p("Secuencia de demostración: registrar los controles del DW; mostrar el mes seleccionado en el tablero; ejecutar una actualización legítima del DW mediante el Proyecto 1 si se dispone de datos nuevos; pulsar Actualizar en Power BI; y contrastar los nuevos controles. Si el DW no cambió, los números deben permanecer iguales. Cambiar un filtro demuestra interactividad, pero no una actualización del origen.")
    p("Permisos recomendados para una cuenta lectora: CONNECT en chinook_dw, USAGE en public y SELECT en fact_sales y las cuatro dimensiones. El SQL opcional acceso_lector.sql prepara esa cuenta sin modificar datos. Las contraseñas se establecen aparte y no se guardan en el SQL ni en Git.")
    h("8. Distribución de una defensa de 20 minutos")
    table(["Tiempo", "Participación", "Contenido"], [
        ["0–2 min", "Brian", "Problema, continuidad con Proyecto 1 y modelo estrella."],
        ["2–6 min", "Cristopher", "Ingresos, ingreso por comprador y comparación mensual."],
        ["6–10 min", "Jeremy", "Compradores activos, conjuntos de retención y Bullet Chart."],
        ["10–14 min", "Brian", "Unidades, género líder y flujo Sankey."],
        ["14–18 min", "Miguel", "Países, top cinco artistas, mapa y árbol."],
        ["18–20 min", "Equipo", "Comprobación de resultados, límites y preguntas."],
    ])
    page()
    h("9. Preguntas para estudiar y defender")
    qa = [
        ("¿Qué aporta Power BI?", "Convierte las tablas del DW en un modelo con relaciones, medidas y visualizaciones interactivas. Permite filtrar y comparar sin reescribir una consulta SQL para cada pregunta."),
        ("¿Qué diferencia existe entre Staging, DW y tablero?", "Staging recibe y comprueba los datos de origen; el DW los organiza para análisis; el tablero comunica medidas calculadas sobre ese DW."),
        ("¿Por qué no contar las filas de Ventas como clientes?", "Cada fila es una línea de factura. Un comprador puede generar varias líneas; por eso se cuentan claves distintas de compradores."),
        ("¿Qué significa la retención de diciembre de 2013?", "De los siete compradores de noviembre, uno también compró en diciembre. No significa que solo uno de los 59 clientes históricos haya regresado alguna vez."),
        ("¿Por qué 0 % no es lo mismo que Sin base?", "Cero significa que se pudo comparar y ningún cliente regresó. Sin base significa que no existen compradores del mes anterior para construir el denominador."),
        ("¿Qué hace CALCULATE con PREVIOUSMONTH?", "Obtiene las fechas anteriores y evalúa allí la medida. REMOVEFILTERS retira el filtro del mes actual para no intersectar dos meses incompatibles."),
        ("¿Por qué distinguir porcentaje de puntos porcentuales?", "Pasar de retención 10 % a 15 % equivale a +5 puntos porcentuales y a un crecimiento relativo de 50 %. La resta de tasas mide puntos porcentuales."),
        ("¿Por qué TOPN tiene dos criterios?", "El ingreso ordena a los artistas y su identificador desempata. Así el numerador representa como máximo cinco artistas."),
        ("¿Por qué hay colores rojos en valores positivos?", "Un nivel positivo puede haber empeorado frente al mes anterior. En concentración, una subida también puede representar mayor dependencia."),
        ("¿La información cambia en tiempo real?", "No en este diseño de Importación. Los filtros recalculan inmediatamente sobre la copia; Actualizar consulta PostgreSQL para traer cambios del origen."),
        ("¿Qué fue difícil técnicamente?", "Alinear el grano de línea de factura con indicadores mensuales; comparar conjuntos de clientes entre meses; distinguir cero de vacío; evitar redondeo prematuro del ingreso por comprador; y demostrar que DAX coincide con una referencia independiente."),
        ("¿Qué decisiones permite tomar?", "Priorizar investigaciones sobre caídas de ingresos, continuidad de compradores y dependencia del catálogo. Los datos orientan la decisión; no prueban por sí solos las causas de los cambios."),
    ]
    for question, answer in qa:
        h(question, 2)
        p(answer)
    page()
    h("Referencias y procedencia")
    p("Balanced Scorecard Institute. (s. f.). Balanced scorecard basics. https://balancedscorecard.org/bsc-basics-overview/")
    p("Centers for Disease Control and Prevention. (s. f.). SMART framework. https://www.cdc.gov/youth-advisory-councils/action-plans/smart-framework.html")
    p("Microsoft. (s. f.-a). Understand star schema and the importance for Power BI. https://learn.microsoft.com/en-us/power-bi/guidance/star-schema")
    p("Microsoft. (s. f.-b). Data refresh in Power BI. https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-data")
    p("Microsoft. (s. f.-c). PostgreSQL connector. https://learn.microsoft.com/en-us/power-query/connectors/postgresql")
    p("Microsoft. (s. f.-d). Decomposition tree. https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-decomposition-tree")
    p("Microsoft. (s. f.-e). Power BI visuals: Bullet Chart y Sankey. https://github.com/microsoft/powerbi-visuals-bulletchart · https://github.com/microsoft/powerbi-visuals-sankey")
    p("Fuentes del equipo: KPIs.docx aprobado, enunciado Proyecto # 2 Minera de Datos.pdf, esquema sql/create_dw.sql, base chinook_dw y cálculos independientes registrados en la carpeta validacion. Se permite asistencia de IA según el enunciado; cada integrante debe comprender y poder explicar las medidas que presenta.")


def shade(cell, fill):
    element = OxmlElement("w:shd")
    element.set(qn("w:fill"), fill)
    cell._tc.get_or_add_tcPr().append(element)


def make_docx():
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin, section.bottom_margin = Cm(2), Cm(2)
    section.left_margin, section.right_margin = Cm(2.2), Cm(2.2)
    base = doc.styles["Normal"]
    base.font.name, base.font.size = "Calibri", Pt(10.5)
    base.paragraph_format.space_after = Pt(7)
    base.paragraph_format.line_spacing = 1.12
    for name, size in [("Title", 28), ("Heading 1", 20), ("Heading 2", 12)]:
        doc.styles[name].font.name = "Calibri"
        doc.styles[name].font.size = Pt(size)
        doc.styles[name].font.color.rgb = RGBColor.from_string(INK if name != "Heading 2" else TEAL)
    section.header.paragraphs[0].text = "INNOVA  /  CHINOOK                                      PROYECTO 02 · MINERÍA DE DATOS"
    section.header.paragraphs[0].style = doc.styles["Caption"]
    footer = section.footer.paragraphs[0]
    footer.text = "UTN · Grupo Innova                                                     "
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    doc.core_properties.title = "Proyecto 2 - Tablero gerencial de Chinook"
    doc.core_properties.author = "Brian Rodriguez; Cristopher Quiros; Jeremy Rodriguez; Miguel Cruz"
    for block in BLOCKS:
        if block[0] == "h":
            doc.add_heading(block[1], level=block[2])
        elif block[0] == "p":
            doc.add_paragraph(block[1])
        elif block[0] == "page":
            doc.add_page_break()
        elif block[0] == "code":
            para = doc.add_paragraph()
            run = para.add_run(block[1])
            run.font.name, run.font.size = "Consolas", Pt(8)
            para.paragraph_format.line_spacing = 1
        elif block[0] == "table":
            rows = block[1]
            tbl = doc.add_table(rows=1, cols=len(rows[0]))
            tbl.style = "Light Shading Accent 1"
            for i, text in enumerate(rows[0]):
                tbl.rows[0].cells[i].text = text
                shade(tbl.rows[0].cells[i], INK)
                for run in tbl.rows[0].cells[i].paragraphs[0].runs:
                    run.font.color.rgb = RGBColor(255, 255, 255)
                    run.bold = True
            for row in rows[1:]:
                cells = tbl.add_row().cells
                for i, text in enumerate(row):
                    cells[i].text = str(text)
            doc.add_paragraph()
    doc.save(OUT / "Proyecto2_Innova.docx")


def make_pdf():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("BodyInnova", fontName="Helvetica", fontSize=10, leading=13, textColor=colors.HexColor("#" + INK), spaceAfter=7))
    styles.add(ParagraphStyle("HeadingInnova", fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=colors.HexColor("#" + INK), spaceAfter=14))
    styles.add(ParagraphStyle("SubInnova", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#" + TEAL), spaceBefore=6, spaceAfter=6, keepWithNext=True))
    styles.add(ParagraphStyle("CellInnova", fontName="Helvetica", fontSize=8.3, leading=11, spaceAfter=0))
    styles.add(ParagraphStyle("CodeInnova", fontName="Courier", fontSize=7, leading=9, spaceAfter=8))
    story = []
    width = A4[0] - 110
    for block in BLOCKS:
        if block[0] in ["p", "h"]:
            style = "BodyInnova" if block[0] == "p" else "HeadingInnova" if block[2] == 1 else "SubInnova"
            story.append(Paragraph(escape(block[1]), styles[style]))
        elif block[0] == "page":
            story.append(PageBreak())
        elif block[0] == "code":
            story.append(Preformatted(block[1], styles["CodeInnova"], maxLineLength=96))
        elif block[0] == "table":
            data = [[Paragraph(escape(str(cell)), styles["CellInnova"]) for cell in row] for row in block[1]]
            n = len(data[0])
            widths = [width / n] * n
            if n == 2:
                widths = [width * .28, width * .72]
            tbl = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#" + PALE)),
                                     ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                     ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#" + TEAL)),
                                     ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")]),
                                     ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                                     ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
            story += [tbl, Spacer(1, 10)]
    def furniture(canvas, document):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#" + INK))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(55, A4[1] - 28, "INNOVA / CHINOOK                                      UTN · PROYECTO 02")
        canvas.setStrokeColor(colors.HexColor("#" + TEAL))
        canvas.line(55, A4[1] - 35, A4[0] - 55, A4[1] - 35)
        canvas.drawRightString(A4[0] - 55, 28, str(document.page))
        canvas.restoreState()
    SimpleDocTemplate(str(OUT / "Proyecto2_Innova.pdf"), pagesize=A4, leftMargin=55, rightMargin=55,
                      topMargin=55, bottomMargin=45, title="Proyecto 2 - Tablero gerencial de Chinook",
                      author="Brian, Cristopher, Jeremy y Miguel").build(story, onFirstPage=furniture, onLaterPages=furniture)


if __name__ == "__main__":
    if VALID["errores"]:
        raise SystemExit("Hay diferencias DAX pendientes: no se genera un documento que afirme validación correcta")
    content()
    make_docx()
    make_pdf()
    print(json.dumps({"docx": str(OUT / "Proyecto2_Innova.docx"), "pdf": str(OUT / "Proyecto2_Innova.pdf")}))
