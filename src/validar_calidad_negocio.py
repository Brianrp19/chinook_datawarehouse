from pathlib import Path
import numpy as np
import pandas as pd
from extract_staging import extract_staging_data


def validar_calidad_negocio(raw_data: dict | None = None):

    errores = []

    if raw_data is None:
        raw_data = extract_staging_data()

    # Carga de datasets necesarios desde Staging
    customer = raw_data.get("Customer", raw_data.get("customer")).copy()
    employee = raw_data.get("Employee", raw_data.get("employee")).copy()
    invoice = raw_data.get("Invoice", raw_data.get("invoice")).copy()
    invoice_line = raw_data.get("InvoiceLine", raw_data.get("invoice_line")).copy()
    track = raw_data.get("Track", raw_data.get("track")).copy()

    print("=" * 70)
    print("VALIDACIONES DE CALIDAD Y REGLAS DE NEGOCIO")
    print("=" * 70)

    # ==========================================================
    # 1. PRECIOS Y CANTIDADES
    # ==========================================================
    print("\n--- 1. PRECIOS Y CANTIDADES ---")

    print("\n1.1 InvoiceLine con UnitPrice <= 0")
    res_inv_price = invoice_line[invoice_line["UnitPrice"] <= 0]
    print(res_inv_price)
    print(f"Cantidad: {len(res_inv_price)}")

    print("\n1.2 InvoiceLine con Quantity <= 0")
    res_inv_qty = invoice_line[invoice_line["Quantity"] <= 0]
    print(res_inv_qty)
    print(f"Cantidad: {len(res_inv_qty)}")

    print("\n1.3 Track con UnitPrice <= 0")
    res_trk_price = track[track["UnitPrice"] <= 0]
    print(res_trk_price)
    print(f"Cantidad: {len(res_trk_price)}")

    print("\n1.4 Track con Milliseconds <= 0")
    res_trk_ms = track[track["Milliseconds"] <= 0]
    print(res_trk_ms)
    print(f"Cantidad: {len(res_trk_ms)}")

    # ==========================================================
    # 2. VALIDACION Y RANGO DE FECHAS
    # ==========================================================
    print("\n--- 2. FECHAS Y RANGOS TEMPORALES ---")

    # Parsear InvoiceDate
    invoice["InvoiceDate_parsed"] = pd.to_datetime(invoice["InvoiceDate"], errors="coerce")
    fechas_invalidas = invoice[invoice["InvoiceDate_parsed"].isna()]
    print(f"\n2.1 Fechas invalidas en Invoice.InvoiceDate: {len(fechas_invalidas)}")

    if len(fechas_invalidas) == 0:
        min_date = invoice["InvoiceDate_parsed"].min()
        max_date = invoice["InvoiceDate_parsed"].max()
        print(f"    Rango disponible: Desde {min_date.date()} hasta {max_date.date()}")
        print(f"    Total de facturas en el periodo: {len(invoice)}")

    # Parsear fechas de Employee
    employee["BirthDate_parsed"] = pd.to_datetime(employee["BirthDate"], errors="coerce")
    employee["HireDate_parsed"] = pd.to_datetime(employee["HireDate"], errors="coerce")
    emp_fechas_invalidas = employee[employee["BirthDate_parsed"].isna() | employee["HireDate_parsed"].isna()]
    print(f"\n2.2 Fechas invalidas en Employee: {len(emp_fechas_invalidas)}")

    # Consistencia: fecha contratacion posterior a fecha nacimiento
    emp_fechas_inconsistentes = employee[employee["HireDate_parsed"] <= employee["BirthDate_parsed"]]
    print(f"2.3 Empleados con HireDate <= BirthDate: {len(emp_fechas_inconsistentes)}")

    # ==========================================================
    # 3. CONSISTENCIA DE TOTALES (Invoice vs InvoiceLine)
    # ==========================================================
    print("\n--- 3. CONSISTENCIA DE TOTALES (Invoice vs InvoiceLine) ---")

    invoice_line["CalculatedLineTotal"] = invoice_line["UnitPrice"] * invoice_line["Quantity"]
    line_totals = (
        invoice_line.groupby("InvoiceId")["CalculatedLineTotal"]
        .sum()
        .round(2)
        .reset_index(name="LineTotalSum")
    )

    comparacion_totales = pd.merge(
        invoice[["InvoiceId", "Total"]],
        line_totals,
        on="InvoiceId",
        how="outer"
    )

    # Comparar con tolerancia para evitar problemas de redondeo float
    diferencias = comparacion_totales[
        comparacion_totales["Total"].isna() |
        comparacion_totales["LineTotalSum"].isna() | (
            np.abs(comparacion_totales["Total"] 
            - comparacion_totales["LineTotalSum"]) > 0.01
        ) 
    ]

    print(f"\n3.1 Facturas con discrepancia entre Invoice.Total y suma de InvoiceLine:")
    print(f"    Total facturas discrepantes: {len(diferencias)}")
    if not diferencias.empty:
        print(diferencias.head(10))
    else:
        print("    -> PERFECTO: Todas las facturas coinciden exactamente con la suma de sus lineas.")

    # ==========================================================
    # 4. DUPLICADOS EN CAMPOS IDENTIFICADORES Y EMAILS
    # ==========================================================
    print("\n--- 4. EMAILS Y UNICIDAD ---")

    emails_cust_duplicados = customer[customer["Email"].duplicated(keep=False)]
    print(f"\n4.1 Correos duplicados en Customer: {len(emails_cust_duplicados)}")
    if not emails_cust_duplicados.empty:
        print(emails_cust_duplicados[["CustomerId", "FirstName", "LastName", "Email"]])

    emails_emp_duplicados = employee[employee["Email"].duplicated(keep=False)]
    print(f"4.2 Correos duplicados en Employee: {len(emails_emp_duplicados)}")

    # ==========================================================
    # 5. NULOS EN CAMPOS CRITICOS DE NEGOCIO
    # ==========================================================
    print("\n--- 5. NULOS EN CAMPOS CRITICOS ---")

    campos_criticos = {
        "Customer": (customer, ["CustomerId", "FirstName", "LastName", "Email", "Country"]),
        "Invoice": (invoice, ["InvoiceId", "CustomerId", "InvoiceDate", "Total"]),
        "InvoiceLine": (invoice_line, ["InvoiceLineId", "InvoiceId", "TrackId", "UnitPrice", "Quantity"]),
        "Track": (track, ["TrackId", "Name", "AlbumId", "MediaTypeId", "GenreId", "UnitPrice", "Milliseconds"]),
    }

    for tabla, (df, cols) in campos_criticos.items():
        nulos = df[cols].isnull().sum()
        nulos_detectados = nulos[nulos > 0]
        if nulos_detectados.empty:
            print(f"    - {tabla}: CERO nulos en campos criticos ({', '.join(cols)})")
        else:
            print(f"    - {tabla} CON NULOS EN CRITICOS: {dict(nulos_detectados)}")

    print("\n" + "=" * 70)
    print("FIN DE VALIDACION DE CALIDAD Y REGLAS DE NEGOCIO")
    print("=" * 70)

    controles = {
        "Precios de ventas no positivos": len(res_inv_price),
        "Cantidades de ventas no positivas": len(res_inv_qty),
        "Precios de tracks no positivos": len(res_trk_price),
        "Duración de tracks no positiva": len(res_trk_ms),
        "Fechas inválidas en Invoice": len(fechas_invalidas),
        "Fechas inválidas en Employee": len(emp_fechas_invalidas),
        "Fechas inconsistentes en Employee": len(emp_fechas_inconsistentes),
        "Facturas con discrepancia de totales": len(diferencias),
    }

    for descripcion, cantidad in controles.items():
        if cantidad > 0:
            errores.append(f"{descripcion}: {cantidad} casos detectados")

    for nombre, (df, columnas) in campos_criticos.items():
        nulos = df[columnas].isnull().sum()
        for columna, cantidad in nulos.items():
            if cantidad > 0:
                errores.append(f"{nombre}.{columna}: {cantidad} valores nulos")
       
    cantidades = pd.to_numeric(invoice_line["Quantity"], errors="coerce")

    cantiades_invalidas = ( cantidades.isna() 
        | ~np.isfinite(cantidades) 
        | cantidades.mod(1).ne(0)
    )

    if cantiades_invalidas.any():
        errores.append(
            "Cantidades no enteras o invalidas: "
            f"{int(cantiades_invalidas.sum())} casos detectados"
        )

    if errores:
        raise ValueError(
            "Errores de calidad y reglas de negocio encontrados:\n" + "\n".join(errores)
        )

    if not errores:
        print("No se encontraron errores de calidad ni violaciones de reglas de negocio.")


if __name__ == "__main__":
    validar_calidad_negocio()    
