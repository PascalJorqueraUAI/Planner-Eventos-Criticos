import os
import tempfile
import unittest

from tests.utilidades import AHORA, servicio_de_prueba


class TestRepositorioCentralizado(unittest.TestCase):
    def setUp(self):
        self.servicio = servicio_de_prueba()
        self.repo = self.servicio.repo

    def test_actualizar_registra_historial_con_valor_anterior_y_nuevo(self):
        self.repo.actualizar("casos", "CASO-1055", {"estado_judicial": "En tramitación"},
                             "CRM", "Integración", "Actualización de caso desde CRM", AHORA)
        registro = self.repo.listar("historial")[-1]
        self.assertEqual(registro["caso_id"], "CASO-1055")
        self.assertEqual(registro["cambios"], {"estado_judicial": ["Notificado", "En tramitación"]})

    def test_actualizar_marca_ultima_actualizacion_del_caso(self):
        self.repo.actualizar("casos", "CASO-1055", {"estado_comercial": "En negociación"},
                             "CRM", "Integración", "Actualización", AHORA)
        self.assertEqual(self.repo.obtener("casos", "CASO-1055")["ultima_actualizacion"], "2026-10-26T09:00:00")

    def test_actualizar_sin_cambios_no_ensucia_el_historial(self):
        antes = len(self.repo.listar("historial"))
        self.repo.actualizar("casos", "CASO-1055", {"estado_judicial": "Notificado"},
                             "CRM", "Integración", "Actualización", AHORA)
        self.assertEqual(len(self.repo.listar("historial")), antes)

    def test_exportar_una_hoja_csv_por_coleccion(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivos = self.repo.exportar_csv(directorio)
            self.assertEqual(len(archivos), 8)
            self.assertTrue(all(os.path.exists(a) for a in archivos))

    def test_actualizacion_desde_crm_dispara_deteccion(self):
        respuesta = self.servicio.actualizar_caso(
            "CASO-1055",
            {"estado_judicial": "Orden de incautación vigente", "estado_comercial": "En negociación",
             "fecha_diligencia": "2026-10-27T10:00:00"},
            "CRM",
        )
        codigos = [e["codigo"] for e in respuesta["deteccion"]["eventos_nuevos"]]
        self.assertEqual(codigos, ["EC-04"])

    def test_campo_no_editable_es_rechazado(self):
        with self.assertRaises(ValueError):
            self.servicio.actualizar_caso("CASO-1055", {"monto_deuda": 1}, "CRM")


if __name__ == "__main__":
    unittest.main()
