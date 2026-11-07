"""Pruebas unitarias de controles de integridad, calidad de negocio y esquema DW."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.etl.load import verify_dw_data
from src.etl.transform import transformar_datos
from src.validations.validar_calidad_negocio import validar_calidad_negocio
from src.validations.validar_integridad import validar_integridad
from src.validations.validar_modelo_dw import validar_modelo_dw
from tests.helpers import build_sample_staging_data


class TestValidacionesStagingYModeloDW(unittest.TestCase):
    def setUp(self):
        self.staging_data = build_sample_staging_data()
        with contextlib.redirect_stdout(io.StringIO()):
            self.dw_data = transformar_datos(self.staging_data)

    def test_datos_staging_validos_aprueban_integridad_y_negocio(self):
        with contextlib.redirect_stdout(io.StringIO()):
            validar_integridad(self.staging_data)
            validar_calidad_negocio(self.staging_data)

    def test_integridad_rechaza_clave_primaria_duplicada(self):
        corrupto = build_sample_staging_data()
        corrupto["customer"].loc[1, "CustomerId"] = 1
        with self.assertRaises(ValueError):
            validar_integridad(corrupto)

    def test_integridad_rechaza_clave_foranea_huerfana(self):
        corrupto = build_sample_staging_data()
        corrupto["invoice"].loc[0, "CustomerId"] = 999
        with self.assertRaises(ValueError):
            validar_integridad(corrupto)

    def test_integridad_rechaza_tabla_faltante(self):
        corrupto = build_sample_staging_data()
        del corrupto["track"]
        with self.assertRaises(KeyError):
            validar_integridad(corrupto)

    def test_calidad_negocio_rechaza_precio_no_positivo(self):
        corrupto = build_sample_staging_data()
        corrupto["invoice_line"].loc[0, "UnitPrice"] = 0.0
        corrupto["invoice"].loc[0, "Total"] = 0.99
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                validar_calidad_negocio(corrupto)

    def test_calidad_negocio_rechaza_discrepancia_total_factura(self):
        corrupto = build_sample_staging_data()
        corrupto["invoice"].loc[0, "Total"] = 99.99
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                validar_calidad_negocio(corrupto)

    def test_calidad_negocio_rechaza_fecha_contratacion_inconsistente(self):
        corrupto = build_sample_staging_data()
        corrupto["employee"].loc[0, "HireDate"] = "1950-01-01 00:00:00"
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                validar_calidad_negocio(corrupto)

    def test_calidad_negocio_rechaza_nulo_en_campo_critico(self):
        corrupto = build_sample_staging_data()
        corrupto["customer"].loc[0, "Email"] = np.nan
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                validar_calidad_negocio(corrupto)

    def test_modelo_dw_rechaza_tabla_faltante(self):
        incompleto = dict(self.dw_data)
        del incompleto["dim_track"]
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                validar_modelo_dw(incompleto)

    def test_modelo_dw_rechaza_texto_fuera_de_limite_varchar(self):
        invalido = {k: v.copy() for k, v in self.dw_data.items()}
        invalido["dim_customer"].loc[0, "country"] = "X" * 51  # VARCHAR(50)
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                validar_modelo_dw(invalido)

    def test_modelo_dw_valida_rango_int32_vs_bigint64(self):
        # bytes es BIGINT (64 bits): un valor mayor a 2^31 - 1 es válido
        valido_bigint = {k: v.copy() for k, v in self.dw_data.items()}
        valido_bigint["dim_track"]["bytes"] = valido_bigint["dim_track"]["bytes"].astype("int64")
        valido_bigint["dim_track"].loc[0, "bytes"] = 3_000_000_000
        with contextlib.redirect_stdout(io.StringIO()):
            validar_modelo_dw(valido_bigint)

        # milliseconds es INT (32 bits): superar 2^31 - 1 debe fallar
        invalido_int32 = {k: v.copy() for k, v in self.dw_data.items()}
        invalido_int32["dim_track"]["milliseconds"] = invalido_int32["dim_track"]["milliseconds"].astype("int64")
        invalido_int32["dim_track"].loc[0, "milliseconds"] = 3_000_000_000
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                validar_modelo_dw(invalido_int32)

    def test_modelo_dw_rechaza_referencia_huerfana_en_fact_sales(self):
        invalido = {k: v.copy() for k, v in self.dw_data.items()}
        invalido["fact_sales"].loc[0, "track_key"] = 999
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                validar_modelo_dw(invalido)

    def test_verify_dw_data_exige_staging_data_con_invoice_line(self):
        with self.assertRaises(ValueError):
            verify_dw_data(None, None)
        with self.assertRaises(ValueError):
            verify_dw_data(None, {"album": self.staging_data["album"]})


if __name__ == "__main__":
    unittest.main()
