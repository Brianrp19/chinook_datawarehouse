from pathlib import Path
import pandas as pd


def get_raw_data_dir() -> Path:
    """Retorna la ruta al directorio con los archivos CSV crudos."""
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "data" / "raw"


def explorar_archivos():
    """Lee y analiza la estructura y calidad inicial de los datos CSV en data/raw."""
    raw_dir = get_raw_data_dir()
    csv_files = sorted(raw_dir.glob("*.csv"))

    if not csv_files:
        print(f"No se encontraron archivos .csv en: {raw_dir}")
        return

    print("=" * 70)
    print("EXPLORACION DE DATOS - CHINOOK DATA WAREHOUSE")
    print(f"Ruta: {raw_dir}")
    print(f"Total de archivos CSV encontrados: {len(csv_files)}")
    print("=" * 70)

    resumen = []

    for file_path in csv_files:
        nombre = file_path.name
        try:
            # En Windows/Latin datasets a veces puede haber encoding utf-8 o latin1
            try:
                df = pd.read_csv(file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding="latin1")

            filas, columnas = df.shape
            nulos_totales = df.isnull().sum().sum()
            duplicados = df.duplicated().sum()

            resumen.append(
                {
                    "Archivo": nombre,
                    "Filas": filas,
                    "Columnas": columnas,
                    "Total Nulos": nulos_totales,
                    "Duplicados": duplicados,
                }
            )

            print(f"\n>>> Archivo: {nombre}")
            print(f"    Dimensiones: {filas} filas x {columnas} columnas")
            print(f"    Columnas: {list(df.columns)}")
            print(f"    Valores nulos por columna:")
            nulls = df.isnull().sum()
            nulls_con_valores = nulls[nulls > 0]
            if not nulls_con_valores.empty:
                for col, cant in nulls_con_valores.items():
                    pct = (cant / filas) * 100
                    print(f"      - {col}: {cant} ({pct:.1f}%)")
            else:
                print("      (Sin valores nulos)")

            if duplicados > 0:
                print(f"    Filas duplicadas: {duplicados}")

        except Exception as e:
            print(f"Error al leer {nombre}: {e}")

    # Tabla resumen final
    print("\n" + "=" * 70)
    print("RESUMEN GENERAL DE ARCHIVOS")
    print("=" * 70)
    df_resumen = pd.DataFrame(resumen)
    print(df_resumen.to_string(index=False))


if __name__ == "__main__":
    explorar_archivos()
1
