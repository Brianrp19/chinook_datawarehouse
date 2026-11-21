"""Construye las cuatro páginas PBIR. No consulta ni modifica PostgreSQL."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "Proyecto2_Innova.Report"
DEFINITION = REPORT / "definition"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
INK, TEAL, AMBER = "#16324F", "#00A6A6", "#F2A541"
BG, MUTED, WHITE = "#EFF4F8", "#68798B", "#FFFFFF"
SANK, BULLET = "sankey02300D1BE6F5427989F3DE31CCA9E0F32020", "BulletChart1443347686880"
CATALOG = json.loads((ROOT / "documentacion/catalogo_kpis.json").read_text(encoding="utf-8"))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def uid(text):
    return hashlib.sha256(text.encode()).hexdigest()[:20]


def expr(value):
    if isinstance(value, bool):
        value = str(value).lower()
    elif isinstance(value, (int, float)):
        value = f"{value}D"
    else:
        value = "'" + value.replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": value}}}


def color(hex_value):
    return {"solid": {"color": expr(hex_value)}}


def field(table, name, measure=False):
    return {"Measure" if measure else "Column": {
        "Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def projection(table, name, measure=False):
    return {"field": field(table, name, measure), "queryRef": f"{table}.{name}", "nativeQueryRef": name}


def obj(properties, selector=None):
    entry = {"properties": properties}
    if selector:
        entry["selector"] = selector
    return [entry]


def chrome(title=None, background=WHITE, padding=14):
    return {
        "title": obj({"show": expr(bool(title)), "text": expr(title or ""),
                      "fontSize": expr(12), "fontFamily": expr("Segoe UI Semibold"),
                      "fontColor": color(INK), "titleWrap": expr(True)}),
        "subTitle": obj({"show": expr(False)}),
        "background": obj({"show": expr(bool(background)), "color": color(background or WHITE), "transparency": expr(0)}),
        "border": obj({"show": expr(False)}),
        "dropShadow": obj({"show": expr(bool(background)), "preset": expr("Custom"), "position": expr("Outer"),
                           "color": color(INK), "transparency": expr(94), "shadowDistance": expr(2),
                           "shadowBlur": expr(6), "shadowSpread": expr(0), "angle": expr(90)}),
        "visualHeader": obj({"show": expr(True), "foreground": color(MUTED)}),
        "padding": obj({side: expr(padding) for side in ["top", "bottom", "left", "right"]}),
    }


class Page:
    def __init__(self, name, title, subtitle, owner, index):
        self.id = uid("page:" + name)
        self.path = DEFINITION / "pages" / self.id
        self.visuals = []
        self.interactions = []
        self.metadata = {"$schema": SCHEMA + "page/2.1.0/schema.json", "name": self.id,
                         "displayName": name, "displayOption": "FitToPage", "height": 720, "width": 1280,
                         "objects": {"background": obj({"color": color(BG), "transparency": expr(0)}),
                                     "outspace": obj({"color": color(BG), "transparency": expr(0)})}}
        self.text("rail", "", 0, 0, 184, 720, bg=INK)
        self.text("brand", "INNOVA", 22, 27, 145, 40, size=24, fg=WHITE, bold=True)
        self.text("brand-sub", "CHINOOK / INTELIGENCIA\nCOMERCIAL", 22, 73, 150, 58, size=11, fg="#9FC8D4")
        self.text("edition", "PROYECTO 02\nMINERÍA DE DATOS", 22, 668, 150, 40, size=11, fg="#9FC8D4")
        self.text("title", title, 208, 25, 810, 45, size=28, bold=True)
        self.text("subtitle", subtitle, 210, 75, 820, 30, size=12, fg=MUTED)
        self.text("number", f"0{index} / 04", 1140, 30, 115, 32, size=14, fg=TEAL, bold=True)
        self.month = self.slicer("month", "Fecha", "Periodo", "Mes de análisis", 208, 112, 240, "2013-12")
        self.slicer("country", "Clientes", "País", "País del cliente", 464, 112, 258)
        self.text("context", "Histórico 2009–2013 · UM: unidad monetaria\nActualizar consulta el DW; los filtros recalculan el modelo.",
                  750, 120, 500, 60, size=11, fg=MUTED)
        self.text("footer", "Verde: evolución favorable · Rojo: desfavorable · Gris: sin variación/base. Comparación histórica, sin metas numéricas aprobadas.",
                  208, 680, 1050, 29, size=10, fg=MUTED)

    def add(self, key, typ, x, y, width, height, roles=None, objects=None, title=None, bg=WHITE, padding=14):
        name = uid(self.id + key)
        index = len(self.visuals)
        visual = {"visualType": typ, "visualContainerObjects": chrome(title, bg, padding), "drillFilterOtherVisuals": True}
        if roles:
            visual["query"] = {"queryState": {role: {"projections": entries} for role, entries in roles.items()}}
        if objects:
            visual["objects"] = objects
        data = {"$schema": SCHEMA + "visualContainer/2.9.0/schema.json", "name": name,
                "position": {"x": x, "y": y, "z": index * 1000, "width": width, "height": height, "tabOrder": index * 1000},
                "visual": visual}
        self.visuals.append(data)
        return data

    def text(self, key, text, x, y, width, height, size=12, fg=INK, bg=None, bold=False):
        runs = [{"textRuns": [{"value": line, "textStyle": {"fontFamily": "Segoe UI Semibold" if bold else "Segoe UI",
                            "fontSize": f"{size}px", "color": fg}}]} for line in text.split("\n")]
        return self.add(key, "textbox", x, y, width, height,
                        objects={"general": obj({"paragraphs": runs})}, bg=bg, padding=0)

    def slicer(self, key, table, column, title, x, y, width, selection=None):
        objects = {"data": obj({"mode": expr("Dropdown")}),
                   "header": obj({"show": expr(True), "text": expr(title), "textSize": expr(10), "fontColor": color(INK)}),
                   "items": obj({"textSize": expr(11), "fontColor": color(INK)})}
        if selection:
            objects["selection"] = obj({"singleSelect": expr(True), "strictSingleSelect": expr(True), "selectAllCheckboxEnabled": expr(False)})
            key_field = {"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": column}}
            objects["general"] = obj({"filter": {"filter": {"Version": 2,
                "From": [{"Name": "d", "Entity": table, "Type": 0}],
                "Where": [{"Condition": {"In": {"Expressions": [key_field], "Values": [[{"Literal": {"Value": "'" + selection + "'"}}]]}}}]}}})
        return self.add(key, "slicer", x, y, width, 80, {"Values": [projection(table, column)]}, objects, padding=8)

    def kpi(self, number, short, hint, x, width=512):
        k = next(item for item in CATALOG if item["id"] == f"KPI-{number:02}")
        table, name = k["tabla_modelo"], k["nombre"]
        cfield = {"solid": {"color": {"expr": field(table, f"KPI-{number:02} color", True)}}}
        self.add(f"kpi{number}", "cardVisual", x, 208, width, 132,
                 {"Data": [projection(table, name, True)]},
                 {"value": obj({"fontSize": expr(42 if width >= 400 else 34), "fontFamily": expr("Bahnschrift"), "fontColor": cfield,
                                "horizontalAlignment": expr("left"), "showBlankAs": expr("Sin base"), "textWrap": expr(False)}, {"id": "default"}),
                  "label": obj({"show": expr(True), "text": expr(short), "position": expr("aboveValue"),
                                "fontSize": expr(12 if width >= 400 else 11), "fontColor": color(INK), "textWrap": expr(True)}, {"id": "default"}),
                  "accentBar": obj({"show": expr(True), "color": color(TEAL), "position": expr("Left"), "width": expr(3)}, {"id": "default"}),
                  "outline": obj({"show": expr(False)}, {"id": "default"})}, padding=16)
        self.visuals[-1]["visual"]["objects"]["border"] = obj({"show": expr(False)}, {"id": "default"})
        self.text(f"hint{number}", hint, x + 8, 346, width - 16, 23, size=10 if width >= 400 else 9, fg=MUTED)

    def chart(self, key, typ, title, table, category, measures, x, y, width, height, historical=False):
        objects = {"categoryAxis": obj({"fontSize": expr(10), "labelColor": color(MUTED), "showAxisTitle": expr(False)}),
                   "valueAxis": obj({"fontSize": expr(10), "labelColor": color(MUTED), "showAxisTitle": expr(False),
                                     "gridlineColor": color("#DFE7EF"), "gridlineShow": expr(True)}),
                   "legend": obj({"show": expr(len(measures) > 1), "position": expr("Top"), "fontSize": expr(10)}),
                   "dataPoint": obj({"defaultColor": color(TEAL)}),
                   "labels": obj({"show": expr(typ != "lineChart"), "fontSize": expr(10), "color": color(INK)})}
        if typ == "lineChart":
            objects["lineStyles"] = obj({"strokeWidth": expr(3), "strokeColor": color(TEAL), "showMarker": expr(False), "lineChartType": expr("linear")})
            if table == "Fecha":
                category = "Inicio mes"
                objects["categoryAxis"][0]["properties"]["axisType"] = expr("Scalar")
        vis = self.add(key, typ, x, y, width, height,
                       {"Category": [projection(table, category)], "Y": [projection(t, m, True) for t, m in measures]},
                       objects, title)
        if historical:
            self.interactions.append({"source": self.month["name"], "target": vis["name"], "type": "NoFilter"})
        return vis

    def navigation(self, pages):
        for i, page in enumerate(pages):
            labels = ["01  Ingresos", "02  Clientes", "03  Catálogo", "04  Mercados"]
            active = page.id == self.id
            self.add("nav" + str(i), "actionButton", 14, 174 + 60 * i, 156, 46,
                     objects={
                         "text": [{"properties": {"show": expr(True)}}, {"properties": {"text": expr(labels[i]), "fontSize": expr(12),
                                   "fontColor": color(WHITE if active else "#B7CDD9"), "horizontalAlignment": expr("left")}, "selector": {"id": "default"}}],
                         "fill": [{"properties": {"show": expr(True)}}, {"properties": {"fillColor": color("#28516A" if active else INK)}, "selector": {"id": "default"}}],
                         "outline": obj({"show": expr(False)}), "icon": obj({"show": expr(False)})}, bg=None, padding=8)
            self.visuals[-1]["visual"]["visualContainerObjects"]["visualLink"] = obj({
                "show": expr(True), "type": expr("PageNavigation"), "navigationSection": expr(page.id),
                "tooltip": expr("Abrir " + page.metadata["displayName"])})

    def write(self):
        names = [visual["name"] for visual in self.visuals]
        if len(names) != len(set(names)):
            raise ValueError("Dos visuales comparten identificador en " + self.metadata["displayName"])
        old_owner = self.path / "visuals" / uid(self.id + "owner") / "visual.json"
        if old_owner.exists():
            old_owner.unlink()
            old_owner.parent.rmdir()
        self.metadata["visualInteractions"] = self.interactions
        save(self.path / "page.json", self.metadata)
        for visual in self.visuals:
            output = self.path / "visuals" / visual["name"] / "visual.json"
            if visual["visual"]["visualType"] == "decompositionTreeVisual" and output.exists():
                previous = json.loads(output.read_text(encoding="utf-8"))
                if "expansionStates" in previous.get("visual", {}):
                    visual["visual"]["expansionStates"] = previous["visual"]["expansionStates"]
            save(output, visual)


def main():
    # Desktop omite estas referencias al guardar. Se restauran para validar el proyecto.
    for path, schema in [(ROOT / "Proyecto2_Innova.pbip", "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json"),
                         (REPORT / "definition.pbir", "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json")]:
        item = json.loads(path.read_text(encoding="utf-8"))
        item["$schema"] = schema
        save(path, item)
    pages = [Page("01 Ingresos", "Ingresos y valor del cliente", "¿Cuánto vendemos y cuánto aporta cada comprador?", "Cristopher Quiros", 1),
             Page("02 Clientes", "Clientes que compran y regresan", "Actividad mensual y retención entre meses consecutivos.", "Jeremy Rodriguez", 2),
             Page("03 Catálogo", "Volumen y mezcla del catálogo", "Crecimiento de unidades y dependencia del género líder.", "Brian Rodriguez", 3),
             Page("04 Mercados", "Alcance y concentración comercial", "Países con compras y peso de los cinco artistas principales.", "Miguel Cruz", 4)]
    a, b, c, d = pages
    a.kpi(1, "KPI 01 · Crecimiento mensual de ingresos", "(Ingresos actuales − anteriores) / anteriores", 208)
    a.kpi(2, "KPI 02 · Ingreso por cliente comprador", "Ingresos / clientes que compraron en el mes · UM/cliente", 744)
    a.chart("trend", "lineChart", "Ingresos mensuales · histórico completo", "Fecha", "Periodo", [("Ventas", "Ingresos")], 208, 376, 650, 284, True)
    a.chart("country-income", "clusteredBarChart", "Ingresos por país · mes seleccionado", "Clientes", "País", [("Ventas", "Ingresos")], 878, 376, 378, 284)
    b.kpi(3, "KPI 03 · Clientes compradores activos", "Un cliente cuenta una vez aunque compre varias líneas", 208)
    b.kpi(4, "KPI 04 · Retención mensual de clientes", "Compradores de ambos meses / compradores del mes previo", 744)
    b.add("bullet", BULLET, 208, 376, 512, 138,
          {"Category": [projection("Fecha", "Periodo")], "Value": [projection("Clientes", "Clientes compradores", True)],
           "TargetValue": [projection("Clientes", "Clientes mes anterior", True)]},
          objects={"colors": obj({"bulletColor": color(TEAL), "fill": color(TEAL), "categoryColor": color(INK)}),
                   "labels": obj({"fontSize": expr(11), "fontFamily": expr("Segoe UI"), "labelColor": color(INK)}),
                   "axis": obj({"axisFontSize": expr(10), "axisFontFamily": expr("Segoe UI"), "axisColor": color(MUTED), "axisPrecision": expr(0)}),
                   "tooltips": obj({"valueCustomName": expr("Compradores actuales"), "targetCustomName": expr("Compradores del mes anterior")})},
          title="Compradores actuales vs. mes previo · referencia")
    b.text("bullet-note", "La marca compara con el mes anterior; no representa una meta aprobada.", 222, 520, 482, 45, size=11, fg=MUTED)
    b.add("retained", "cardVisual", 208, 565, 512, 95,
          {"Data": [projection("Clientes", "Clientes retenidos", True)]},
          {"value": obj({"fontSize": expr(28), "fontColor": color(INK)}, {"id": "default"}),
           "label": obj({"show": expr(True), "text": expr("Compradores presentes en ambos meses"), "fontSize": expr(11)}, {"id": "default"})})
    b.chart("retention-trend", "lineChart", "Retención mensual · histórico completo", "Fecha", "Periodo", [("Clientes", "Tasa de retención mensual de clientes")], 744, 376, 512, 284, True)
    c.kpi(5, "KPI 05 · Crecimiento mensual de unidades", "(Unidades actuales − anteriores) / anteriores", 208)
    c.kpi(6, "KPI 06 · Concentración del género líder", "Ingresos del género líder / ingresos del mes", 744)
    c.chart("units-trend", "lineChart", "Unidades mensuales · histórico completo", "Fecha", "Periodo", [("Ventas", "Unidades vendidas")], 208, 376, 512, 284, True)
    c.add("sankey", SANK, 744, 376, 512, 284,
          {"Source": [projection("Clientes", "País")], "Destination": [projection("Canciones", "Género")],
           "Weight": [projection("Ventas", "Ingresos", True)]},
          objects={"labels": obj({"show": expr(True), "fill": color(INK), "fontFamily": expr("Segoe UI"), "fontSize": expr(11)}),
                   "links": obj({"matchNodeColors": expr(True), "matchSourceOrDestination": expr("source"), "showBorder": expr(False)}),
                   "scaleSettings": obj({"provideMinHeight": expr(True)}),
                   "nodes": obj({"nodesWidth": expr(12), "fill": color(TEAL)})}, title="Flujo de ingresos · país → género")
    d.kpi(7, "KPI 07 · Países con ventas", "Países con compradores en el mes", 208, 248)
    d.kpi(8, "KPI 08 · Ingresos del top 5", "Participación de los cinco artistas líderes", 472, 248)
    d.add("map", "map", 208, 376, 512, 284,
          {"Category": [projection("Clientes", "País")], "Size": [projection("Ventas", "Ingresos", True)],
           "Tooltips": [projection("Clientes", "Clientes compradores", True)]}, title="Mapa de ingresos · mes seleccionado")
    d.add("tree", "decompositionTreeVisual", 744, 208, 512, 452,
          {"Analyze": [projection("Ventas", "Ingresos", True)],
           "ExplainBy": [projection("Clientes", "País"), projection("Canciones", "Género"), projection("Canciones", "Artista")]},
          objects={"categoryLabels": obj({"categoryLabelFontFamily": expr("Segoe UI"), "categoryLabelFontSize": expr(10), "categoryLabelFontColor": color(INK)}),
                   "dataLabels": obj({"dataLabelFontFamily": expr("Bahnschrift"), "dataLabelFontSize": expr(10), "dataLabelFontColor": color(INK)}),
                   "tree": obj({"density": expr("dense"), "barsPerLevel": expr(5), "responsiveLayout": expr(True)}),
                   "dataBars": obj({"positiveBarColor": color(TEAL), "negativeBarColor": color("#CB4B4B")}),
                   "levelHeader": obj({"levelTitleFontFamily": expr("Segoe UI Semibold"), "levelTitleFontSize": expr(11), "levelTitleFontColor": color(INK)})},
          title="¿De dónde provienen los ingresos? · expandí +")
    for page in pages:
        page.navigation(pages)
        page.write()
    # El scaffold inicial está vacío: se conserva fuera de pageOrder para no borrar archivos del usuario.
    existing = json.loads((DEFINITION / "pages/pages.json").read_text(encoding="utf-8"))
    existing.update(pageOrder=[page.id for page in pages], activePageName=pages[0].id)
    save(DEFINITION / "pages/pages.json", existing)
    theme = {"name": "Innova-2e2a814b.json", "dataColors": [TEAL, AMBER, "#587CA0", "#D4534D", "#78B7AC", INK],
             "background": WHITE, "foreground": INK, "tableAccent": TEAL, "good": "#00897B", "bad": "#CB4B4B", "neutral": MUTED,
             "textClasses": {"label": {"fontFace": "Segoe UI", "fontSize": 11, "color": INK},
                             "title": {"fontFace": "Segoe UI Semibold", "fontSize": 13, "color": INK},
                             "callout": {"fontFace": "Bahnschrift", "fontSize": 36, "color": INK}}}
    save(REPORT / "StaticResources/RegisteredResources" / theme["name"], theme)
    report = json.loads((DEFINITION / "report.json").read_text(encoding="utf-8"))
    report["publicCustomVisuals"] = [SANK, BULLET]
    report["themeCollection"]["customTheme"] = {"name": theme["name"], "type": "RegisteredResources",
          "reportVersionAtImport": report["themeCollection"]["baseTheme"]["reportVersionAtImport"]}
    report["resourcePackages"] = [p for p in report["resourcePackages"] if p["name"] != "RegisteredResources"] + [
        {"name": "RegisteredResources", "type": "RegisteredResources", "items": [{"name": theme["name"], "path": theme["name"], "type": "CustomTheme"}]}]
    save(DEFINITION / "report.json", report)
    print(json.dumps({"paginas": len(pages), "visuales": sum(len(p.visuals) for p in pages), "kpis": 8}))


if __name__ == "__main__":
    main()
