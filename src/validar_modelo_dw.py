from pathlib import Path
import pandas as pd
from extract_staging import extract_staging_data

# Carga de datasets desde Staging
raw_data = extract_staging_data()
track = raw_data["track"]
album = raw_data["album"]
artist = raw_data["artist"]
invoice = raw_data["invoice"]
customer = raw_data["customer"]
employee = raw_data["employee"]

invoice["InvoiceDate"] = pd.to_datetime(invoice["InvoiceDate"], errors="coerce")

print("=" * 70)
print("VALIDACIONES PREVIAS AL MODELO DATA WAREHOUSE (DESDE STAGING)")
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
