"""Contrasta la salida JSON del MCP de Power BI con la línea base independiente del DW."""
import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "validacion"


def rows_from_mcp(path):
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if envelope.get("is_error"):
        raise ValueError("Power BI devolvió un error; no se acepta como validación")
    data = json.loads(next(c["text"] for c in envelope["content"] if c.get("type") == "text"))["data"]
    if data.get("isTruncated"):
        raise ValueError("La consulta DAX está truncada")
    return data["rows"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resultado", type=Path, help="Resultado JSON de dax_query_operations Execute / Inline")
    args = parser.parse_args()
    actual = rows_from_mcp(args.resultado)
    with (CHECK / "linea_base_mensual.csv").open(encoding="utf-8-sig", newline="") as f:
        expected = list(csv.DictReader(f))
    if len(expected) != len(actual):
        raise AssertionError(f"Meses SQL={len(expected)}; meses DAX={len(actual)}")
    names = list(expected[0])
    checked = 0
    errors = []
    observed = {}
    for item in actual:
        month = item.get("Fecha[Periodo]")
        if month in observed:
            raise AssertionError("Mes repetido en la salida DAX: " + str(month))
        observed[month] = item
    for source in expected:
        month = source["Periodo"]
        if month not in observed:
            errors.append({"periodo": month, "error": "Mes ausente"})
            continue
        item = observed[month]
        for name in names[1:]:
            sql = None if source[name] == "" else float(source[name])
            dax = item.get("[" + name + "]")
            equal = (sql is None and dax is None) or (
                sql is not None and dax is not None and math.isclose(sql, float(dax), rel_tol=1e-10, abs_tol=1e-10))
            if not equal:
                errors.append({"periodo": month, "campo": name, "dw": sql, "dax": dax})
            checked += 1
    summary = {"fuente": "chinook_dw", "motor_dax": "Power BI Desktop / Analysis Services",
               "meses": len(expected), "kpis": 8, "comparaciones_kpi": len(expected) * 8,
               "comparaciones_totales": checked, "errores": errors,
               "tolerancia": {"relativa": 1e-10, "absoluta": 1e-10},
               "nota": "Incluye valores BLANK en el primer mes y cero cuando no hubo clientes retenidos."}
    (CHECK / "resultado_validacion_dax.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
