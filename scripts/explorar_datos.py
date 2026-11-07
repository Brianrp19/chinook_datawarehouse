import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd
from src.etl.extract_staging import extract_staging_data

def explorar_tablas():
    # Explora las tablas extraídas desde PostgreSQL Staging y muestra información relevante.
    datos = extract_staging_data()

    print("=" * 70)
    print("Exploracion de datos de postgreSQL Staging:")
    print(f"Total de tablas extraidas: {len(datos)} ")
    print("=" * 70)

    resumen = []

    for nombre_tabla, df in datos.items():
        filas, columnas = df.shape
        nulos_totales = int(df.isna().sum().sum())
        duplicados = int(df.duplicated().sum())

        resumen.append({
            "Tabla": nombre_tabla,
            "Filas": filas,
            "Columnas": columnas,
            "Nulos Totales": nulos_totales,
            "Duplicados": duplicados
        })

        print(f"\nTabla: {nombre_tabla}")
        print(f"Dimensiones: {filas} filas x {columnas} columnas")
        print(f"Columnas: {list(df.columns)}")
        print(f"Valores nulos por columna:")

        nulos = df.isna().sum()
        columnas_nulos = nulos[nulos > 0]

        if columnas_nulos.empty:
            print("No se encontraron valores nulos.")
        else:
            for columna, cantidad in columnas_nulos.items():
                proporcion = cantidad / filas * 100 if filas else 0
                print(f"- {columna}: {cantidad}")
                print(f"{proporcion:.2f}% de la columna")
        print(f"Filas duplicadas: {duplicados}")

    print("=" * 70)    
    print("resumen general de staging")
    print("=" * 70)
    print(pd.DataFrame(resumen).to_string(index=False))


if __name__ == "__main__":
    explorar_tablas()

