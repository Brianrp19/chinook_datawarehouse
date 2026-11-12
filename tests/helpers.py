#Datos sintéticos de referencia con estructura idéntica a PostgreSQL Staging.
from __future__ import annotations

import numpy as np
import pandas as pd


def build_sample_staging_data() -> dict[str, pd.DataFrame]:
    """Construye un conjunto mínimo consistente de las 11 tablas de Staging."""
    return {
        "artist": pd.DataFrame(
            {
                "ArtistId": [1, 2],
                "Name": ["AC/DC", "Accept"],
            }
        ),
        "album": pd.DataFrame(
            {
                "AlbumId": [1, 2],
                "Title": ["For Those About To Rock", "Balls to the Wall"],
                "ArtistId": [1, 2],
            }
        ),
        "genre": pd.DataFrame(
            {
                "GenreId": [1],
                "Name": ["Rock"],
            }
        ),
        "media_type": pd.DataFrame(
            {
                "MediaTypeId": [1],
                "Name": ["MPEG audio file"],
            }
        ),
        "playlist": pd.DataFrame(
            {
                "PlaylistId": [1, 2],
                "Name": ["Music", "90's Music"],
            }
        ),
        "playlist_track": pd.DataFrame(
            {
                "PlaylistId": [1, 2, 1],
                "TrackId": [1, 1, 2],
            }
        ),
        "employee": pd.DataFrame(
            {
                "EmployeeId": [1, 3],
                "LastName": ["Adams", "Peacock"],
                "FirstName": ["Andrew", "Jane"],
                "Title": ["General Manager", "Sales Support Agent"],
                "ReportsTo": [np.nan, 1.0],
                "BirthDate": ["1962-02-18 00:00:00", "1973-08-29 00:00:00"],
                "HireDate": ["2002-08-14 00:00:00", "2002-04-01 00:00:00"],
                "Address": ["11120 Jasper Ave NW", "1111 6 Ave SW"],
                "City": ["Edmonton", "Calgary"],
                "State": ["AB", "AB"],
                "Country": ["Canada", "Canada"],
                "PostalCode": ["T5K 2N1", "T2P 5M5"],
                "Phone": ["+1 (780) 428-9482", "+1 (403) 262-3443"],
                "Email": ["andrew@chinookcorp.com", "jane@chinookcorp.com"],
            }
        ),
        "customer": pd.DataFrame(
            {
                "CustomerId": [1, 2],
                "FirstName": ["Luís", "Leonie"],
                "LastName": ["Gonçalves", "Köhler"],
                "Company": ["Embraer", np.nan],
                "Address": ["Av. Brigadeiro Faria Lima, 2170", "Theodor-Heuss-Straße 34"],
                "City": ["São José dos Campos", "Stuttgart"],
                "State": ["SP", np.nan],
                "Country": ["Brazil", "Germany"],
                "PostalCode": ["12227-000", "070174"],
                "Phone": ["+55 (12) 3923-5555", "+49 0711 2842222"],
                "Email": ["luisg@embraer.com.br", "leonekohler@surfeu.de"],
                "SupportRepId": [3, 3],
            }
        ),
        "track": pd.DataFrame(
            {
                "TrackId": [1, 2],
                "Name": ["For Those About To Rock (We Salute You)", "Balls to the Wall"],
                "AlbumId": [1, 2],
                "MediaTypeId": [1, 1],
                "GenreId": [1, 1],
                "Composer": ["Angus Young, Malcolm Young, Brian Johnson", np.nan],
                "Milliseconds": [343719, 342562],
                "Bytes": [11170334, 5510424],
                "UnitPrice": [0.99, 0.99],
            }
        ),
        "invoice": pd.DataFrame(
            {
                "InvoiceId": [1, 2],
                "CustomerId": [1, 2],
                "InvoiceDate": ["2012-01-05 00:00:00", "2013-06-15 00:00:00"],
                "Total": [1.98, 0.99],
            }
        ),
        "invoice_line": pd.DataFrame(
            {
                "InvoiceLineId": [1, 2, 3],
                "InvoiceId": [1, 1, 2],
                "TrackId": [1, 2, 2],
                "UnitPrice": [0.99, 0.99, 0.99],
                "Quantity": [1, 1, 1],
            }
        ),
    }
