from pathlib import Path
import pandas as pd



def validar_integridad():
    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"


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

    datos = {
        nombre: pd.read_csv(raw_dir / f"{nombre}.csv") for nombre in claves.keys()
    }

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

    # en resumidas cuentas entran los datos del arreglo de arriva con las relaciones para poder saber si hay erroes o si hay integridad antes de pasar al data warehouse
    for origen, columna, destino, clave, permite_nulos in relaciones:
        valores = datos [origen][columna]
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
