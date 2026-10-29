"""El paquete de evidencia se genera completo y sus cifras son coherentes."""

import json
import os
import shutil
import tempfile
import unittest

import evidencia
from tests.utilidades import AHORA


class TestEvidencia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directorio = tempfile.mkdtemp(prefix="evidencia_")
        cls.resultado = evidencia.generar(cls.directorio, incluir_pruebas=False, dias_simulacion=2, inicio=AHORA,
                                          semillas_sensibilidad=(1, 2))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directorio, ignore_errors=True)

    def test_genera_todos_los_archivos(self):
        for nombre in ("README.md", "deteccion.md", "recorrido_demo.md", "simulacion.md",
                       "checklist_capturas.md", "metricas.json"):
            self.assertTrue(os.path.exists(os.path.join(self.directorio, nombre)), nombre)
        self.assertTrue(os.path.exists(os.path.join(self.directorio, "exportaciones", "Cobgestion_casos.csv")))

    def test_deteccion_coincide_con_lo_esperado(self):
        d = self.resultado["deteccion"]
        self.assertEqual(d["casos_correctos"], d["casos_evaluados"])
        self.assertEqual(d["eventos_detectados"], d["eventos_esperados"])
        self.assertEqual(d["tareas_con_responsable"], d["tareas"])

    def test_recorrido_muestra_el_cierre_coordinado_y_la_alerta_inmediata(self):
        with open(os.path.join(self.directorio, "recorrido_demo.md"), encoding="utf-8") as f:
            texto = f.read()
        self.assertIn("Cierre coordinado", texto)
        self.assertIn("**0 minutos** entre la recepción y la alerta", texto)
        self.assertIn("Cerrado", texto)

    def test_simulacion_alerta_todos_los_avisos(self):
        s = self.resultado["simulacion"]
        self.assertGreater(s["avisos_registrados"], 0)
        self.assertEqual(s["avisos_con_alerta_judicial_pct"], 100.0)
        self.assertEqual(s["tareas_con_responsable_pct"], 100.0)
        with open(os.path.join(self.directorio, "metricas.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["simulacion"]["avisos_registrados"], s["avisos_registrados"])


    def test_simulacion_reporta_el_rango_y_no_lo_presenta_como_hallazgo(self):
        sens = self.resultado["sensibilidad"]
        self.assertEqual(sens["semillas"], [1, 2])
        self.assertLessEqual(sens["cumplimiento_sla_pct"]["min"], sens["cumplimiento_sla_pct"]["max"])
        with open(os.path.join(self.directorio, "simulacion.md"), encoding="utf-8") as f:
            texto = f.read()
        self.assertIn("Sensibilidad", texto)
        self.assertIn("no es un hallazgo", texto)
        # El tiempo de respuesta simulado no depende de la hora: el reporte no puede atribuirle el resultado.
        self.assertIn("No se modela el horario laboral", texto)
        self.assertNotIn("llegan también de noche y en fin de semana. Por eso", texto)


if __name__ == "__main__":
    unittest.main()
