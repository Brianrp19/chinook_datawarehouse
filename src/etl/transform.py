import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd
from src.etl.extract_staging import extract_staging_data


def build_dim_date(invoice_df: pd.DataFrame) -> pd.DataFrame:
    """Genera la dimensión fecha cubriendo todo el rango temporal del negocio."""
    invoice_dates = pd.to_datetime(invoice_df["InvoiceDate"])
    start_year = invoice_dates.min().year
    end_year = invoice_dates.max().year

    date_range = pd.date_range(
        start=f"{start_year}-01-01",
        end=f"{end_year}-12-31",
        freq="D"
    )

    df_date = pd.DataFrame({"full_date": date_range})
    df_date["date_key"] = df_date["full_date"].dt.strftime("%Y%m%d").astype(int)
    df_date["year"] = df_date["full_date"].dt.year
    df_date["quarter"] = df_date["full_date"].dt.quarter
    df_date["month"] = df_date["full_date"].dt.month
    df_date["month_name"] = df_date["full_date"].dt.strftime("%B")
    df_date["day"] = df_date["full_date"].dt.day
    df_date["day_name"] = df_date["full_date"].dt.strftime("%A")
    # dayofweek en pandas: 0=Lunes, 6=Domingo -> DW estandar 1=Lunes, 7=Domingo
    df_date["day_of_week"] = df_date["full_date"].dt.dayofweek + 1
    df_date["is_weekend"] = df_date["day_of_week"].isin([6, 7])

    column_order = [
        "date_key", "full_date", "year", "quarter", "month",
        "month_name", "day", "day_name", "day_of_week", "is_weekend"
    ]
    return df_date[column_order]


def build_dim_employee(employee_df: pd.DataFrame) -> pd.DataFrame:
    """Construye la dimensión empleado resolviendo jerarquía de supervisión."""
    df = employee_df.copy()

    # Nombre completo
    df["full_name"] = df["FirstName"].str.strip() + " " + df["LastName"].str.strip()

    # Parsear fechas
    df["birth_date"] = pd.to_datetime(df["BirthDate"]).dt.date
    df["hire_date"] = pd.to_datetime(df["HireDate"]).dt.date

    # Resolver nombre del supervisor (ReportsTo -> EmployeeId)
    manager_names = df.set_index("EmployeeId")["full_name"].to_dict()
    df["reports_to_name"] = df["ReportsTo"].map(manager_names).fillna("Sin Supervisor (Nivel Superior)")

    # Renombrar columnas al estándar del DW
    df = df.rename(
        columns={
            "EmployeeId": "employee_id",
            "FirstName": "first_name",
            "LastName": "last_name",
            "Title": "title",
            "ReportsTo": "reports_to",
            "Address": "address",
            "City": "city",
            "State": "state",
            "Country": "country",
            "PostalCode": "postal_code",
            "Phone": "phone",
            "Email": "email",
        }
    )

    # Clave sustituta (SK)
    df = df.sort_values("employee_id").reset_index(drop=True)
    df.insert(0, "employee_key", range(1, len(df) + 1))

    column_order = [
        "employee_key", "employee_id", "first_name", "last_name", "full_name",
        "title", "reports_to", "reports_to_name", "birth_date", "hire_date",
        "address", "city", "state", "country", "postal_code", "phone", "email"
    ]
    return df[column_order]


def build_dim_customer(customer_df: pd.DataFrame) -> pd.DataFrame:
    """Construye la dimensión cliente estandarizando nombres y atributos."""
    df = customer_df.copy()

    df["full_name"] = df["FirstName"].str.strip() + " " + df["LastName"].str.strip()
    df["Company"] = df["Company"].fillna("Particular")

    df = df.rename(
        columns={
            "CustomerId": "customer_id",
            "FirstName": "first_name",
            "LastName": "last_name",
            "Company": "company",
            "Address": "address",
            "City": "city",
            "State": "state",
            "Country": "country",
            "PostalCode": "postal_code",
            "Phone": "phone",
            "Email": "email",
            "SupportRepId": "support_rep_id",
        }
    )

    # Clave sustituta (SK)
    df = df.sort_values("customer_id").reset_index(drop=True)
    df.insert(0, "customer_key", range(1, len(df) + 1))

    column_order = [
        "customer_key", "customer_id", "first_name", "last_name", "full_name",
        "company", "address", "city", "state", "country", "postal_code",
        "phone", "email", "support_rep_id"
    ]
    return df[column_order]


def build_dim_track(
    track_df: pd.DataFrame,
    album_df: pd.DataFrame,
    artist_df: pd.DataFrame,
    genre_df: pd.DataFrame,
    media_type_df: pd.DataFrame,
    playlist_track_df: pd.DataFrame,
) -> pd.DataFrame:
    """Desnormaliza la jerarquía musical: Track + Album + Artist + Genre + MediaType + Playlists."""
    # Conteo de apariciones en playlists por track
    playlist_counts = (
        playlist_track_df.groupby("TrackId")["PlaylistId"]
        .nunique()
        .reset_index(name="playlist_count")
    )

    # Album + Artist
    album_artist = album_df.merge(
        artist_df.rename(columns={"Name": "artist_name"}),
        on="ArtistId",
        how="left"
    ).rename(columns={"Title": "album_title"})

    # Track + Album/Artist
    track_merged = track_df.merge(
        album_artist[["AlbumId", "album_title", "ArtistId", "artist_name"]],
        on="AlbumId",
        how="left"
    )

    # + Genre
    track_merged = track_merged.merge(
        genre_df.rename(columns={"Name": "genre_name"}),
        on="GenreId",
        how="left"
    )

    # + MediaType
    track_merged = track_merged.merge(
        media_type_df.rename(columns={"Name": "media_type_name"}),
        on="MediaTypeId",
        how="left"
    )

    # + Playlists count
    track_merged = track_merged.merge(
        playlist_counts,
        on="TrackId",
        how="left"
    )
    track_merged["playlist_count"] = track_merged["playlist_count"].fillna(0).astype(int)

    # Cálculos derivados
    track_merged["duration_seconds"] = (track_merged["Milliseconds"] / 1000.0).round(2)
    track_merged["duration_minutes"] = (track_merged["Milliseconds"] / 60000.0).round(2)
    track_merged["Composer"] = track_merged["Composer"].fillna("Desconocido / No asignado")

    track_merged = track_merged.rename(
        columns={
            "TrackId": "track_id",
            "Name": "track_name",
            "AlbumId": "album_id",
            "ArtistId": "artist_id",
            "MediaTypeId": "media_type_id",
            "GenreId": "genre_id",
            "Composer": "composer",
            "Milliseconds": "milliseconds",
            "Bytes": "bytes",
            "UnitPrice": "unit_price",
        }
    )

    # Clave sustituta (SK)
    track_merged = track_merged.sort_values("track_id").reset_index(drop=True)
    track_merged.insert(0, "track_key", range(1, len(track_merged) + 1))

    column_order = [
        "track_key", "track_id", "track_name", "album_id", "album_title",
        "artist_id", "artist_name", "media_type_id", "media_type_name",
        "genre_id", "genre_name", "composer", "milliseconds",
        "duration_seconds", "duration_minutes", "bytes", "unit_price",
        "playlist_count"
    ]
    return track_merged[column_order]


def build_fact_sales(
    invoice_line_df: pd.DataFrame,
    invoice_df: pd.DataFrame,
    dim_customer: pd.DataFrame,
    dim_employee: pd.DataFrame,
    dim_track: pd.DataFrame,
) -> pd.DataFrame:
    """Construye la tabla de hechos con grano a nivel de detalle de factura (InvoiceLine)."""
    # 1. Unir InvoiceLine con Invoice para obtener CustomerId y InvoiceDate
    sales = invoice_line_df.merge(
        invoice_df[["InvoiceId", "CustomerId", "InvoiceDate"]],
        on="InvoiceId",
        how="inner"
    )

    # 2. Generar date_key a partir de InvoiceDate
    sales["date_key"] = pd.to_datetime(sales["InvoiceDate"]).dt.strftime("%Y%m%d").astype(int)

    # 3. Mapear claves sustitutas de dim_customer (customer_key y support_rep_id)
    sales = sales.merge(
        dim_customer[["customer_id", "customer_key", "support_rep_id"]],
        left_on="CustomerId",
        right_on="customer_id",
        how="inner"
    )

    # 4. Mapear clave sustituta de dim_employee usando el support_rep_id del cliente
    sales = sales.merge(
        dim_employee[["employee_id", "employee_key"]],
        left_on="support_rep_id",
        right_on="employee_id",
        how="inner"
    )

    # 5. Mapear clave sustituta de dim_track
    sales = sales.merge(
        dim_track[["track_id", "track_key"]],
        left_on="TrackId",
        right_on="track_id",
        how="inner"
    )

    # 6. Calcular métricas
    sales["unit_price"] = sales["UnitPrice"].round(2)
    sales["quantity"] = sales["Quantity"].astype(int)
    sales["total_amount"] = (sales["unit_price"] * sales["quantity"]).round(2)

    # 7. Clave sustituta de la tabla de hechos
    sales = sales.sort_values(["InvoiceId", "InvoiceLineId"]).reset_index(drop=True)
    sales.insert(0, "sales_key", range(1, len(sales) + 1))

    # 8. Renombrar claves degeneradas y ordenar columnas
    sales = sales.rename(
        columns={
            "InvoiceId": "invoice_id",
            "InvoiceLineId": "invoice_line_id",
        }
    )

    column_order = [
        "sales_key", "date_key", "customer_key", "track_key", "employee_key",
        "invoice_id", "invoice_line_id", "unit_price", "quantity", "total_amount"
    ]
    return sales[column_order]


def transformar_datos(staging_data: dict | None = None):
    """Ejecuta el pipeline completo de transformación (T) y retorna los DataFrames listos."""
    print("Iniciando Transformacion (T) del Data Warehouse...")
    stg = staging_data if staging_data is not None else extract_staging_data()

    dim_date = build_dim_date(stg["invoice"])
    dim_employee = build_dim_employee(stg["employee"])
    dim_customer = build_dim_customer(stg["customer"])
    dim_track = build_dim_track(
        stg["track"], stg["album"], stg["artist"], stg["genre"], stg["media_type"], stg["playlist_track"]
    )
    fact_sales = build_fact_sales(
        stg["invoice_line"], stg["invoice"], dim_customer, dim_employee, dim_track
    )

    print("\n--- RESUMEN DE TRANSFORMACION ---")
    print(f"dim_date:     {dim_date.shape[0]} filas, {dim_date.shape[1]} columnas")
    print(f"dim_employee: {dim_employee.shape[0]} filas, {dim_employee.shape[1]} columnas")
    print(f"dim_customer: {dim_customer.shape[0]} filas, {dim_customer.shape[1]} columnas")
    print(f"dim_track:    {dim_track.shape[0]} filas, {dim_track.shape[1]} columnas")
    print(f"fact_sales:   {fact_sales.shape[0]} filas, {fact_sales.shape[1]} columnas")
    print(f"Total ventas acumuladas: ${fact_sales['total_amount'].sum():,.2f}")

    return {
        "dim_date": dim_date,
        "dim_employee": dim_employee,
        "dim_customer": dim_customer,
        "dim_track": dim_track,
        "fact_sales": fact_sales,
    }


if __name__ == "__main__":
    transformar_datos()
