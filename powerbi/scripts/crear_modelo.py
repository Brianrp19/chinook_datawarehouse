"""Genera la definición del modelo y los ocho KPIs aprobados, sin credenciales."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent / ".system_generated" / "proyecto2"
WORK.mkdir(parents=True, exist_ok=True)

MEASURES = []


def measure(table, name, expression, fmt="#,##0.00", description="", folder="Base", hidden=False):
    item = {"name": name, "expression": expression.strip(), "formatString": fmt,
            "description": description, "displayFolder": folder}
    if hidden:
        item["isHidden"] = True
    MEASURES.append((table, item))


measure("Ventas", "Ingresos", "SUM('Ventas'[Importe])", '#,##0.00 "UM"',
        "Ingresos por ventas del DW. La fuente no identifica moneda ni costos; no representa utilidad.")
measure("Ventas", "Unidades vendidas", "SUM('Ventas'[Unidades])", "#,##0",
        "Suma de unidades vendidas, incluyendo los contenidos de audio y video del catálogo.")
measure("Clientes", "Clientes compradores", "DISTINCTCOUNT('Ventas'[Clave cliente])", "#,##0",
        "Clientes distintos con ventas en el contexto seleccionado.")
measure("Ventas", "Facturas", "DISTINCTCOUNT('Ventas'[Id factura])", "#,##0",
        "Facturas diferentes: una factura puede contener varias líneas.")
measure("Fecha", "Mes seleccionado", 'SELECTEDVALUE(\'Fecha\'[Periodo], "Seleccione un mes")', "@",
        "Periodo mensual seleccionado. Los KPIs mensuales requieren un único mes.")
measure("Fecha", "Última venta", "MAXX(ALL('Ventas'), RELATED('Fecha'[Fecha]))", "dd/MM/yyyy",
        "Última fecha con venta en la fuente; no confundir con el último día del calendario.")

def previous(expression):
    return """VAR _FechasAnteriores = PREVIOUSMONTH('Fecha'[Fecha])
RETURN
    IF(
        HASONEVALUE('Fecha'[Periodo]),
        CALCULATE(%s, REMOVEFILTERS('Fecha'), _FechasAnteriores)
    )""" % expression

measure("Ventas", "Ingresos mes anterior", previous("[Ingresos]"), '#,##0.00 "UM"',
        "Ingresos del mes calendario inmediatamente anterior. Sin base histórica devuelve BLANK.", "Comparación mensual")
measure("Ventas", "Unidades mes anterior", previous("[Unidades vendidas]"), "#,##0",
        "Unidades del mes anterior; conserva los filtros de país, género y demás dimensiones.", "Comparación mensual")
measure("Clientes", "Clientes mes anterior", previous("[Clientes compradores]"), "#,##0",
        "Número de clientes compradores del mes previo; denominador de la retención.", "Comparación mensual")

measure("Clientes", "Clientes retenidos", """
VAR _FechasAnteriores = PREVIOUSMONTH('Fecha'[Fecha])
VAR _ClientesAntes = CALCULATETABLE(
    VALUES('Ventas'[Clave cliente]), REMOVEFILTERS('Fecha'), _FechasAnteriores
)
VAR _ClientesAhora = VALUES('Ventas'[Clave cliente])
RETURN IF(
    HASONEVALUE('Fecha'[Periodo]) && COUNTROWS(_ClientesAntes) > 0,
    COALESCE(COUNTROWS(INTERSECT(_ClientesAntes, _ClientesAhora)), 0)
)""", "#,##0", "Intersección de compradores del mes actual y del inmediatamente anterior; no clientes históricos acumulados.", "Retención")

KPI = [
    ("KPI-01", "Crecimiento mensual de ingresos", "Cristopher Quiros", "Ventas", """
VAR _Anterior = [Ingresos mes anterior]
RETURN IF(HASONEVALUE('Fecha'[Periodo]), DIVIDE([Ingresos] - _Anterior, _Anterior))
""", "0.0%;-0.0%;0.0%", "Variación de ingresos frente al mes anterior. BLANK cuando no existe base o el denominador es cero.", "mayor", "%"),
    ("KPI-02", "Ingreso promedio por cliente comprador", "Cristopher Quiros", "Clientes", """
IF(HASONEVALUE('Fecha'[Periodo]), DIVIDE(CONVERT([Ingresos], DOUBLE), [Clientes compradores]))
""", '#,##0.00 "UM"', "Ingresos del mes divididos entre clientes distintos que compraron en ese mes. No utiliza todos los clientes del catálogo.", "mayor", "UM/cliente"),
    ("KPI-03", "Clientes compradores activos por mes", "Jeremy Rodriguez", "Clientes", """
IF(HASONEVALUE('Fecha'[Periodo]), [Clientes compradores])
""", "#,##0", "Clientes únicos con al menos una compra en el mes seleccionado.", "mayor", "clientes"),
    ("KPI-04", "Tasa de retención mensual de clientes", "Jeremy Rodriguez", "Clientes", """
IF(HASONEVALUE('Fecha'[Periodo]), DIVIDE([Clientes retenidos], [Clientes mes anterior]))
""", "0.0%", "Compradores presentes en ambos meses / compradores del mes anterior. Cero significa que ninguno volvió; BLANK indica ausencia de base.", "mayor", "%"),
    ("KPI-05", "Crecimiento mensual de unidades vendidas", "Brian Rodriguez", "Ventas", """
VAR _Anterior = [Unidades mes anterior]
RETURN IF(HASONEVALUE('Fecha'[Periodo]), DIVIDE([Unidades vendidas] - _Anterior, _Anterior))
""", "0.0%;-0.0%;0.0%", "Cambio de SUM(Unidades) frente al mes anterior; no se confunde la cantidad de una línea con el volumen mensual.", "mayor", "%"),
    ("KPI-06", "Concentración de ingresos por género musical", "Brian Rodriguez", "Canciones", """
VAR _Generos = ADDCOLUMNS(
    VALUES('Canciones'[Género]),
    "__IngresosGenero", CALCULATE([Ingresos])
)
VAR _Lider = MAXX(_Generos, [__IngresosGenero])
RETURN IF(HASONEVALUE('Fecha'[Periodo]), DIVIDE(_Lider, [Ingresos]))
""", "0.0%", "Participación del género de mayores ingresos entre los géneros del contexto seleccionado. Menor concentración favorece diversificación, no equivale por sí sola a mayor rentabilidad.", "menor", "%"),
    ("KPI-07", "Cantidad de países con ventas mensuales", "Miguel Cruz", "Clientes", """
VAR _PaisesConVenta = FILTER(
    VALUES('Clientes'[País]),
    CALCULATE(COUNTROWS('Ventas')) > 0
)
RETURN IF(HASONEVALUE('Fecha'[Periodo]), COUNTROWS(_PaisesConVenta))
""", "#,##0", "Países de clientes que realmente compraron en el mes; no todos los países de la dimensión. La geografía corresponde al cliente actual del DW.", "mayor", "países"),
    ("KPI-08", "Concentración de ingresos en los cinco artistas principales", "Miguel Cruz", "Canciones", """
VAR _Artistas = ADDCOLUMNS(
    VALUES('Canciones'[Id artista]),
    "__IngresosArtista", CALCULATE([Ingresos])
)
VAR _ConVenta = FILTER(_Artistas, NOT ISBLANK([__IngresosArtista]) && [__IngresosArtista] > 0)
VAR _Cinco = TOPN(
    5, _ConVenta,
    [__IngresosArtista], DESC,
    'Canciones'[Id artista], ASC
)
VAR _IngresosTop = SUMX(_Cinco, [__IngresosArtista])
RETURN IF(HASONEVALUE('Fecha'[Periodo]), DIVIDE(_IngresosTop, [Ingresos]))
""", "0.0%", "Ingresos de exactamente los cinco artistas líderes / ingresos del contexto. Se desempata por Id artista para evitar que TOPN incluya más de cinco artistas empatados.", "menor", "%"),
]

for identifier, name, owner, table, expression, fmt, description, direction, unit in KPI:
    measure(table, name, expression, fmt, f"{identifier} | Responsable: {owner}. {description}", "KPIs aprobados")
    if identifier not in {"KPI-01", "KPI-05"}:
        measure(table, f"{identifier} mes anterior", previous(f"[{name}]"), fmt,
                f"Valor del {identifier} en el mes anterior para comparación, no una meta aprobada.", "Comparación mensual")
        measure(table, f"{identifier} cambio", f"""
VAR _Actual = [{name}]
VAR _Anterior = [{identifier} mes anterior]
RETURN IF(NOT ISBLANK(_Actual) && NOT ISBLANK(_Anterior), _Actual - _Anterior)
""", "0.0%;-0.0%;0.0%" if unit == "%" else fmt,
                "Diferencia frente al mes anterior. En tasas representa diferencia de proporciones, no crecimiento relativo.", "Comparación mensual")
    delta = f"[{name}]" if identifier in {"KPI-01", "KPI-05"} else f"[{identifier} cambio]"
    comparator = "> 0" if direction == "mayor" else "< 0"
    measure(table, f"{identifier} color", f"""
VAR _Cambio = {delta}
RETURN SWITCH(
    TRUE(),
    ISBLANK(_Cambio), "#68798B",
    _Cambio = 0, "#68798B",
    _Cambio {comparator}, "#00897B",
    "#CB4B4B"
)
""", "@", "Color condicional según el cambio histórico. No representa cumplimiento de una meta que no fue fijada.", "Formato condicional", True)

measure("Fecha", "Contexto del informe", """
"Datos hasta " & FORMAT([Última venta], "dd/MM/yyyy") & " · Comparación mensual · Importes en UM"
""", "@", "Aclara fecha de corte histórica y unidades monetarias.")

# Nombre en el DW, nombre de negocio y tipo TOM. El nombre de negocio es también
# el nombre de salida de Power Query, por lo que sourceColumn coincide exactamente.
DEFINITIONS = {
    "Ventas": ("fact_sales", [
        ("sales_key", "Clave venta", "int64"), ("date_key", "Clave fecha", "int64"),
        ("customer_key", "Clave cliente", "int64"), ("track_key", "Clave canción", "int64"),
        ("employee_key", "Clave empleado", "int64"), ("invoice_id", "Id factura", "int64"),
        ("invoice_line_id", "Id línea", "int64"), ("quantity", "Unidades", "int64"),
        ("unit_price", "Precio unitario", "decimal"), ("total_amount", "Importe", "decimal"),
    ]),
    "Fecha": ("dim_date", [
        ("date_key", "Clave fecha", "int64"), ("full_date", "Fecha", "dateTime"),
        ("year", "Año", "int64"), ("month", "Mes", "int64"),
        ("month_name", "Nombre mes", "string"), ("quarter", "Trimestre", "int64"),
    ]),
    "Clientes": ("dim_customer", [
        ("customer_key", "Clave cliente", "int64"), ("customer_id", "Id cliente", "int64"),
        ("full_name", "Cliente", "string"), ("country", "País", "string"), ("city", "Ciudad", "string"),
    ]),
    "Canciones": ("dim_track", [
        ("track_key", "Clave canción", "int64"), ("track_id", "Id canción", "int64"),
        ("track_name", "Contenido", "string"), ("genre_name", "Género", "string"),
        ("artist_id", "Id artista", "int64"), ("artist_name", "Artista", "string"),
        ("album_title", "Álbum", "string"), ("media_type_name", "Tipo de medio", "string"),
        ("duration_minutes", "Duración minutos", "decimal"),
    ]),
    "Empleados": ("dim_employee", [
        ("employee_key", "Clave empleado", "int64"), ("employee_id", "Id empleado", "int64"),
        ("full_name", "Empleado de soporte", "string"), ("title", "Cargo", "string"),
    ]),
}


def m_string(value):
    return '"' + value.replace('"', '""') + '"'


def build():
    tables = []
    for name, (source, mappings) in DEFINITIONS.items():
        columns, types, renames = [], [], []
        for original, friendly, dtype in mappings:
            hidden = friendly.startswith(("Clave", "Id ")) or friendly in {"Importe", "Unidades", "Precio unitario"}
            column = {"name": friendly, "dataType": dtype, "sourceColumn": friendly,
                      "summarizeBy": "none", "isHidden": hidden,
                      "description": f"Origen: public.{source}.{original}."}
            if dtype == "decimal":
                column["formatString"] = "#,##0.00"
            if dtype == "dateTime":
                column.update({"formatString": "dd/MM/yyyy", "isKey": True})
            if friendly in {"País", "Ciudad"}:
                column["dataCategory"] = "Country" if friendly == "País" else "City"
            if friendly == "Nombre mes":
                column["sortByColumn"] = "Mes"
            columns.append(column)
            mtype = {"int64": "Int64.Type", "decimal": "Currency.Type", "string": "type text", "dateTime": "type date"}[dtype]
            types.append("{" + m_string(friendly) + ", " + mtype + "}")
            renames.append("{" + m_string(original) + ", " + m_string(friendly) + "}")
        selected = ", ".join(m_string(c[0]) for c in mappings)
        expression = f"""let
    Origen = PostgreSQL.Database(Servidor, BaseDatos, [CreateNavigationProperties=false]),
    Tabla = Origen{{[Schema="public", Item="{source}"]}}[Data],
    Seleccion = Table.SelectColumns(Tabla, {{{selected}}}),
    Nombres = Table.RenameColumns(Seleccion, {{{', '.join(renames)}}}),
    Tipos = Table.TransformColumnTypes(Nombres, {{{', '.join(types)}}})"""
        final_step = "Tipos"
        if name == "Fecha":
            expression += """,
    Periodos = Table.AddColumn(Tipos, "Periodo", each Date.ToText([Fecha], "yyyy-MM"), type text),
    Orden = Table.AddColumn(Periodos, "Orden periodo", each [Año] * 100 + [Mes], Int64.Type)"""
            columns += [
                {"name": "Periodo", "dataType": "string", "sourceColumn": "Periodo", "sortByColumn": "Orden periodo", "summarizeBy": "none"},
                {"name": "Orden periodo", "dataType": "int64", "sourceColumn": "Orden periodo", "isHidden": True, "summarizeBy": "none"},
                {"name": "Inicio mes", "dataType": "dateTime", "type": "calculated",
                 "expression": "DATE('Fecha'[Año], 'Fecha'[Mes], 1)", "formatString": "MMM yyyy", "summarizeBy": "none",
                 "description": "Primer día del mes para graficar todos los meses en un eje temporal continuo."},
            ]
            final_step = "Orden"
        expression += f"\nin\n    {final_step}"
        table = {
            "name": name,
            "description": f"Tabla de negocio importada directamente desde chinook_dw.public.{source}; modelo estrella del Proyecto 1.",
            "columns": columns,
            "measures": [m for target, m in MEASURES if target == name],
            "partitions": [{"name": name, "mode": "import", "source": {"type": "m", "expression": expression}}],
        }
        if name == "Fecha":
            table["dataCategory"] = "Time"
        tables.append(table)

    relationships = []
    for dimension, key in [("Fecha", "Clave fecha"), ("Clientes", "Clave cliente"), ("Canciones", "Clave canción"), ("Empleados", "Clave empleado")]:
        relationships.append({"name": f"Ventas_{dimension}", "fromTable": "Ventas", "fromColumn": key,
                              "toTable": dimension, "toColumn": key, "fromCardinality": "many", "toCardinality": "one",
                              "crossFilteringBehavior": "oneDirection", "isActive": True})
    database = {
        "name": "Proyecto2_Innova", "id": "Proyecto2_Innova", "compatibilityLevel": 1702,
        "model": {"name": "Model", "culture": "es-CR", "sourceQueryCulture": "es-CR",
                  "defaultPowerBIDataSourceVersion": "powerBI_V3", "discourageImplicitMeasures": True,
                  "expressions": [
                      {"name": "Servidor", "kind": "m", "expression": '"localhost:5432" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'},
                      {"name": "BaseDatos", "kind": "m", "expression": '"chinook_dw" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'},
                  ], "tables": tables, "relationships": relationships,
                  "annotations": [{"name": "__PBI_TimeIntelligenceEnabled", "value": "0"}]},
    }
    (WORK / "modelo.bim").write_text(json.dumps(database, ensure_ascii=False, indent=2), encoding="utf-8")
    catalog = [{"id": ident, "nombre": name, "responsable": owner, "tabla_modelo": table,
                "dax": expr.strip(), "formato": fmt, "definicion": desc,
                "sentido_comparacion": direction, "unidad": unit, "meta_numerica_aprobada": None}
               for ident, name, owner, table, expr, fmt, desc, direction, unit in KPI]
    (ROOT / "documentacion").mkdir(exist_ok=True)
    (ROOT / "documentacion" / "catalogo_kpis.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    dax = "DEFINE\n" + "\n\n".join(f"    MEASURE '{table}'[{m['name']}] =\n{m['expression']}" for table, m in MEASURES)
    dax += "\n\nEVALUATE ROW(\"Ingresos\", [Ingresos], \"Facturas\", [Facturas])\n"
    (ROOT / "documentacion" / "medidas_dax.dax").write_text(dax, encoding="utf-8")
    functions = sorted(set(re.findall(r"\b([A-Z][A-Z0-9_]*)\s*\(", dax)))
    print(json.dumps({"modelo": str(WORK / "modelo.bim"), "tablas": len(tables), "relaciones": len(relationships),
                      "medidas": len(MEASURES), "kpis": len(KPI), "funciones_dax": functions}, ensure_ascii=True))


if __name__ == "__main__":
    build()
