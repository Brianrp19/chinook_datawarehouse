from pathlib import Path
import pandas as pd

raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"

# Carga de datasets
track = pd.read_csv(raw_dir / "Track.csv")
album = pd.read_csv(raw_dir / "Album.csv")
artist = pd.read_csv(raw_dir / "Artist.csv")
invoice = pd.read_csv(raw_dir / "Invoice.csv")
customer = pd.read_csv(raw_dir / "Customer.csv")
employee = pd.read_csv(raw_dir / "Employee.csv")

invoice["InvoiceDate"] = pd.to_datetime(invoice["InvoiceDate"], errors="coerce")

print("=" * 70)
print("VALIDACIONES PREVIAS AL MODELO DATA WAREHOUSE")
print("=" * 70)

print("\n=== VALIDACION DE TRACK ===")
print("Track UnitPrice <= 0:   ", len(track[track["UnitPrice"] <= 0]))
print("Track Milliseconds <= 0:", len(track[track["Milliseconds"] <= 0]))
print("Track Bytes <= 0:       ", len(track[track["Bytes"] <= 0]))
print("Track Bytes is null:    ", track["Bytes"].isna().sum())

print("\n=== LONGITUDES MAXIMAS DE TEXTO (VARCHAR) ===")
print("Max len Track.Name:        ", track["Name"].str.len().max())
print("Max len Track.Composer:    ", track["Composer"].dropna().str.len().max())
print("Max len Album.Title:       ", album["Title"].str.len().max())
print("Max len Artist.Name:       ", artist["Name"].str.len().max())
print("Max len Customer.Company:  ", customer["Company"].dropna().str.len().max())
print("Max len Customer.Address:  ", customer["Address"].str.len().max())
print("Max len Customer.City:     ", customer["City"].str.len().max())
print("Max len Customer.State:    ", customer["State"].dropna().str.len().max())
print("Max len Customer.Country:  ", customer["Country"].str.len().max())
print("Max len Customer.Email:    ", customer["Email"].str.len().max())
print("Max len Employee.Title:    ", employee["Title"].str.len().max())

print("\n=== RANGO DE FECHAS FACTURAS ===")
print("Fecha minima:", invoice["InvoiceDate"].min())
print("Fecha maxima:", invoice["InvoiceDate"].max())
print("Total facturas:", len(invoice))
