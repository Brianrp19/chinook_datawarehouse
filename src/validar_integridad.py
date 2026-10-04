from pathlib import Path
import pandas as pd

# Definir ruta hacia data/raw (compatible si se ejecuta desde la raíz o dentro de src)
base_dir = Path(__file__).resolve().parent.parent
raw_dir = base_dir / "data" / "raw"

# Carga de datasets
album = pd.read_csv(raw_dir / "Album.csv")
artist = pd.read_csv(raw_dir / "Artist.csv")
customer = pd.read_csv(raw_dir / "Customer.csv")
employee = pd.read_csv(raw_dir / "Employee.csv")
genre = pd.read_csv(raw_dir / "Genre.csv")
invoice = pd.read_csv(raw_dir / "Invoice.csv")
invoice_line = pd.read_csv(raw_dir / "InvoiceLine.csv")
media_type = pd.read_csv(raw_dir / "MediaType.csv")
playlist = pd.read_csv(raw_dir / "Playlist.csv")
playlist_track = pd.read_csv(raw_dir / "PlaylistTrack.csv")
track = pd.read_csv(raw_dir / "Track.csv")

print("=== INTEGRIDAD REFERENCIAL ===")

print("\nAlbum -> Artist")
print(album[~album["ArtistId"].isin(artist["ArtistId"])])

print("\nTrack -> Album")
print(track[~track["AlbumId"].isin(album["AlbumId"])])

print("\nTrack -> Genre")
print(track[~track["GenreId"].isin(genre["GenreId"])])

print("\nTrack -> MediaType")
print(track[~track["MediaTypeId"].isin(media_type["MediaTypeId"])])

print("\nInvoice -> Customer")
print(invoice[~invoice["CustomerId"].isin(customer["CustomerId"])])

print("\nInvoiceLine -> Invoice")
print(invoice_line[~invoice_line["InvoiceId"].isin(invoice["InvoiceId"])])

# Validaciones complementarias de integridad
print("\nInvoiceLine -> Track")
print(invoice_line[~invoice_line["TrackId"].isin(track["TrackId"])])

print("\nCustomer -> Employee (SupportRepId)")
print(customer[~customer["SupportRepId"].isin(employee["EmployeeId"])])

print("\nPlaylistTrack -> Playlist")
print(playlist_track[~playlist_track["PlaylistId"].isin(playlist["PlaylistId"])])

print("\nPlaylistTrack -> Track")
print(playlist_track[~playlist_track["TrackId"].isin(track["TrackId"])])
