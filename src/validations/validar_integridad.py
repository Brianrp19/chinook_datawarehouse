import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pandas as pd
from etl.extract_staging import extract_staging_data

SOURCE_NAME_MAP = {
    "Album": "album",
    "Artist": "artist",
    "Customer": "customer",
    "Employee": "employee",
    "Genre": "genre",
    "Invoice": "invoice",
    "InvoiceLine": "invoice_line",
    "MediaType": "media_type",
    "Playlist": "playlist",
    "PlaylistTrack": "playlist_track",
    "Track": "track",
}


def validar_integridad(staging_data: dict | None = None):
    claves = {
        "Album": ["AlbumId"],
        "Artist": ["ArtistId"],
        "Customer": ["CustomerId"],
        "Employee": ["EmployeeId"],
        "Genre": ["GenreId"],
        "Invoice": ["InvoiceId"],
        "InvoiceLine": ["InvoiceLineId"],
        "MediaType": ["MediaTypeId"],
        "Playlist": ["PlaylistId"],
        "PlaylistTrack": ["PlaylistId", "TrackId"],
        "Track": ["TrackId"],
    }

    if staging_data is None:
        staging_data = extract_staging_data()

    datos = {}
    for nombre in claves.keys():
        key = SOURCE_NAME_MAP.get(nombre, nombre.lower())
        datos[nombre] = staging_data.get(nombre, staging_data.get(key))
        if datos[nombre] is None:
            raise KeyError(f"No se encontró la tabla {nombre} en los datos extraídos.")

    errores = []

    for nombre, columnas in claves.items():
        tabla = datos[nombre]

        nulos = tabla[columnas].isna().any(axis=1).sum()
        duplicados = tabla.duplicated(subset=columnas).sum()

        if nulos > 0:
            errores.append(f"{nombre}: {nulos} filas con valores nulos en {columnas}")
        if duplicados > 0:
            errores.append(f"{nombre}: {duplicados} filas duplicadas en {columnas}")

    relaciones = [
        ("Album", "ArtistId", "Artist", "ArtistId", False),
        ("Track", "AlbumId", "Album", "AlbumId", False),
        ("Track", "GenreId", "Genre", "GenreId", False),
        ("Track", "MediaTypeId", "MediaType", "MediaTypeId", False),
        ("Invoice", "CustomerId", "Customer", "CustomerId", False),
        ("InvoiceLine", "InvoiceId", "Invoice", "InvoiceId", False),
        ("InvoiceLine", "TrackId", "Track", "TrackId", False),
        ("Customer", "SupportRepId", "Employee", "EmployeeId", False),
        ("PlaylistTrack", "PlaylistId", "Playlist", "PlaylistId", False),
        ("PlaylistTrack", "TrackId", "Track", "TrackId", False),
        ("Employee", "ReportsTo", "Employee", "EmployeeId", True),
    ] 

    # Validación de integridad referencial entre tablas
    for origen, columna, destino, clave, permite_nulos in relaciones:
        valores = datos[origen][columna]
        referencias = datos[destino][clave]

        invalidos = ~valores.isin(referencias)
        if permite_nulos:
            invalidos = invalidos & valores.notna()

        cantidad = int(invalidos.sum())
        if cantidad > 0:
            errores.append(
                f"{origen}.{columna} tiene {cantidad} valores que no existen en {destino}.{clave}"
            )

    if errores:
        raise ValueError(
            "Errores de integridad referencial encontrados:\n" + "\n".join(errores)
        )

    if not errores:
        print("No se encontraron errores de integridad. Todas las relaciones y claves son válidas.")            


if __name__ == "__main__":
    validar_integridad()
