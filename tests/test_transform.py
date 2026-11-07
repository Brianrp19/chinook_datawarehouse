"""Pruebas unitarias para la capa de transformación dimensional (Star Schema)."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.etl.transform import transformar_datos
from src.validations.validar_modelo_dw import validar_modelo_dw
from tests.helpers import build_sample_staging_data


class TestTransformStarSchema(unittest.TestCase):
    def setUp(self):
        self.staging_data = build_sample_staging_data()

    def test_transformar_datos_genera_modelo_estrella_consistente(self):
        with contextlib.redirect_stdout(io.StringIO()):
            dw_data = transformar_datos(self.staging_data)

        self.assertEqual(
            set(dw_data.keys()),
            {"dim_date", "dim_employee", "dim_customer", "dim_track", "fact_sales"},
        )

        # 2012 (bisiesto: 366) + 2013 (365) = 731 días continuos
        self.assertEqual(len(dw_data["dim_date"]), 731)
        self.assertEqual(len(dw_data["dim_employee"]), 2)
        self.assertEqual(len(dw_data["dim_customer"]), 2)
        self.assertEqual(len(dw_data["dim_track"]), 2)
        self.assertEqual(len(dw_data["fact_sales"]), 3)

        # Verificar resolución jerárquica en dim_employee
        emp = dw_data["dim_employee"].set_index("employee_id")
        self.assertEqual(emp.loc[1, "reports_to_name"], "Sin Supervisor (Nivel Superior)")
        self.assertEqual(emp.loc[3, "reports_to_name"], "Andrew Adams")

        # Verificar valores por defecto y preservación de códigos postales en dim_customer
        cust = dw_data["dim_customer"].set_index("customer_id")
        self.assertEqual(cust.loc[2, "company"], "Particular")
        self.assertEqual(cust.loc[2, "postal_code"], "070174")

        # Verificar conteo de playlists y compositor por defecto en dim_track
        trk = dw_data["dim_track"].set_index("track_id")
        self.assertEqual(trk.loc[1, "playlist_count"], 2)
        self.assertEqual(trk.loc[2, "playlist_count"], 1)
        self.assertEqual(trk.loc[2, "composer"], "Desconocido / No asignado")

        # Verificar cuadratura matemática en fact_sales
        sales = dw_data["fact_sales"]
        self.assertAlmostEqual(float(sales["total_amount"].sum()), 2.97, places=2)
        self.assertTrue((sales["total_amount"] == (sales["unit_price"] * sales["quantity"]).round(2)).all())

    def test_modelo_transformado_aprueba_validador_dw(self):
        with contextlib.redirect_stdout(io.StringIO()):
            dw_data = transformar_datos(self.staging_data)
            validar_modelo_dw(dw_data)


if __name__ == "__main__":
    unittest.main()
