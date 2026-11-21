"""Calcula la línea base de los ocho KPIs leyendo el DW, sin escrituras SQL."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg
from dotenv import dotenv_values


PROJECT = Path(__file__).resolve().parents[2]
OUTPUT = PROJECT / "powerbi" / "validacion"
TABLES = ["dim_date", "dim_customer", "dim_employee", "dim_track", "fact_sales"]


def read_reference(env_path: Path):
    values = dotenv_values(env_path, interpolate=False)
    required = ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]
    if any(not values.get(key) for key in required):
        raise ValueError("Faltan datos de conexión del DW en el archivo .env.")
    if values["PGDATABASE"] != "chinook_dw":
        raise ValueError("La fuente esperada del Proyecto 2 es chinook_dw.")
    with psycopg.connect(
        host=values["PGHOST"], port=int(values["PGPORT"]),
        dbname=values["PGDATABASE"], user=values["PGUSER"], password=values["PGPASSWORD"],
        connect_timeout=5, options="-c default_transaction_read_only=on -c statement_timeout=30000",
    ) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM public.{table}").fetchone()[0]
            for table in TABLES
        }
        rows = conn.execute("""
            SELECT d.full_date, f.invoice_id, f.customer_key, f.track_key,
                   f.quantity, f.total_amount, c.country, t.genre_name,
                   t.artist_id, t.artist_name, t.media_type_name
            FROM public.fact_sales f
            JOIN public.dim_date d ON d.date_key=f.date_key
            JOIN public.dim_customer c ON c.customer_key=f.customer_key
            JOIN public.dim_track t ON t.track_key=f.track_key
            ORDER BY d.full_date, f.invoice_line_id
        """).fetchall()
        owner = conn.execute("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()").fetchone()[0]

    if not rows or len(rows) != counts["fact_sales"]:
        raise ValueError("El DW está vacío o alguna relación pierde líneas de venta.")
    by_month = defaultdict(list)
    for row in rows:
        by_month[row[0].replace(day=1)].append(row)
    result = []
    for month, records in sorted(by_month.items()):
        previous_month = date(month.year - (month.month == 1), (month.month - 2) % 12 + 1, 1)
        previous = by_month.get(previous_month)
        cents = sum(int(row[5] * 100) for row in records)
        units = sum(row[4] for row in records)
        customers = {row[2] for row in records}
        previous_customers = {row[2] for row in previous} if previous else set()
        retained = customers & previous_customers
        previous_cents = sum(int(row[5] * 100) for row in previous) if previous else 0
        previous_units = sum(row[4] for row in previous) if previous else 0
        by_genre, by_artist = defaultdict(int), defaultdict(int)
        for row in records:
            by_genre[row[7]] += int(row[5] * 100)
            by_artist[row[8]] += int(row[5] * 100)
        top_artists = sorted(by_artist.items(), key=lambda item: (-item[1], item[0] if item[0] is not None else -1))[:5]
        result.append({
            "Periodo": month.strftime("%Y-%m"),
            "Ingresos": cents / 100,
            "Facturas": len({row[1] for row in records}),
            "Unidades": units,
            "ClientesMesAnterior": len(previous_customers) if previous else None,
            "ClientesRetenidos": len(retained) if previous else None,
            "KPI01_CrecimientoIngresos": (cents - previous_cents) / previous_cents if previous_cents else None,
            "KPI02_IngresoPromedioCliente": cents / 100 / len(customers),
            "KPI03_ClientesActivos": len(customers),
            "KPI04_RetencionClientes": len(retained) / len(previous_customers) if previous_customers else None,
            "KPI05_CrecimientoUnidades": (units - previous_units) / previous_units if previous_units else None,
            "KPI06_ConcentracionGenero": max(by_genre.values()) / cents if cents else None,
            "KPI07_PaisesConVentas": len({row[6] for row in records}),
            "KPI08_ConcentracionTop5Artistas": sum(amount for _, amount in top_artists) / cents if cents else None,
        })
    all_cents = sum(int(row[5] * 100) for row in rows)
    metadata = {
        "fuente": "PostgreSQL / chinook_dw / public",
        "propietario": owner,
        "tablas": counts,
        "primera_venta": str(min(row[0] for row in rows)),
        "ultima_venta": str(max(row[0] for row in rows)),
        "meses_con_ventas": len(result),
        "facturas": len({row[1] for row in rows}),
        "clientes_compradores": len({row[2] for row in rows}),
        "unidades": sum(row[4] for row in rows),
        "ingresos": all_cents / 100,
        "retencion_meses_con_base": sum(r["KPI04_RetencionClientes"] is not None for r in result),
        "retencion_meses_con_recompra": sum((r["ClientesRetenidos"] or 0) > 0 for r in result),
        "metas_aprobadas": None,
        "nota_metas": "El documento aprobado no fija metas numéricas; las comparaciones históricas no son metas.",
        "nota_moneda": "La fuente no contiene un código de moneda. Se muestran unidades monetarias (UM).",
    }
    return metadata, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=PROJECT / ".env")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    metadata, rows = read_reference(args.env)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "linea_base_mensual.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "perfil_dw.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"perfil": metadata, "ultimo_mes": rows[-1]}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
