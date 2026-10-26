import unittest

from tests.utilidades import Reloj, servicio_de_prueba, tareas_del_caso


class TestSeguimientoYCierreCoordinado(unittest.TestCase):
    def setUp(self):
        self.reloj = Reloj()
        self.servicio = servicio_de_prueba(self.reloj)
        self.repo = self.servicio.repo
        self.evento, self.tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")

    def test_tarea_queda_pendiente_hasta_marcarse_atendida(self):
        self.assertEqual(self.tareas["Comercial"]["estado"], "Pendiente")
        self.servicio.atender_tarea(self.tareas["Comercial"]["id"], "Pago confirmado", "Cartola OK", "Comercial")
        self.assertEqual(self.tareas["Comercial"]["estado"], "Atendida")
        self.assertEqual(self.tareas["Comercial"]["resultado"], "Pago confirmado")

    def test_comercial_confirma_pero_el_evento_no_se_cierra_sin_judicial(self):
        """Regla que evita repetir la incautación indebida de $600.000."""
        respuesta = self.servicio.atender_tarea(self.tareas["Comercial"]["id"], "Pago confirmado", "", "Comercial")
        self.assertFalse(respuesta["evento_cerrado"])
        self.assertIn("Judicial", respuesta["motivo_cierre"])
        self.assertEqual(self.evento["estado"], "Abierto")

    def test_evento_se_cierra_cuando_ambas_areas_atienden(self):
        self.servicio.atender_tarea(self.tareas["Comercial"]["id"], "Pago confirmado", "", "Comercial")
        respuesta = self.servicio.atender_tarea(
            self.tareas["Judicial"]["id"], "Diligencia suspendida preventivamente", "Receptor notificado", "Judicial"
        )
        self.assertTrue(respuesta["evento_cerrado"])
        self.assertEqual(self.evento["estado"], "Cerrado")

    def test_resultado_se_aplica_al_repositorio(self):
        self.servicio.atender_tarea(self.tareas["Comercial"]["id"], "Pago confirmado", "", "Comercial")
        self.servicio.atender_tarea(self.tareas["Judicial"]["id"], "Diligencia suspendida preventivamente", "", "Judicial")
        self.assertEqual(self.repo.obtener("avisos", "AVP-0101")["estado"], "confirmado")
        self.assertEqual(self.repo.obtener("casos", "CASO-1052")["estado_judicial"], "Suspendido preventivo por aviso de pago")

    def test_resultado_fuera_del_catalogo_es_rechazado(self):
        with self.assertRaises(ValueError):
            self.servicio.atender_tarea(self.tareas["Comercial"]["id"], "Inventado", "", "Comercial")

    def test_atender_alimenta_el_historial_de_desempeno(self):
        responsable = self.tareas["Judicial"]["responsable_id"]
        antes = len(self.repo.filtrar("historial_desempeno", colaborador_id=responsable))
        self.reloj.avanzar(hours=6)  # SLA de 4 h: fuera de plazo
        self.servicio.atender_tarea(self.tareas["Judicial"]["id"], "Mantener curso de la causa", "", "Judicial")
        registros = self.repo.filtrar("historial_desempeno", colaborador_id=responsable)
        self.assertEqual(len(registros), antes + 1)
        self.assertFalse(registros[-1]["cumplio_sla"])
        self.assertEqual(registros[-1]["horas_resolucion"], 6.0)

    def test_tarea_vencida_se_marca_en_el_estado(self):
        self.reloj.avanzar(hours=5)
        tareas = {t["id"]: t for t in self.servicio.estado()["tareas"]}
        self.assertTrue(tareas[self.tareas["Judicial"]["id"]]["vencida"])
        self.assertFalse(tareas[self.tareas["Comercial"]["id"]]["vencida"])

    def test_no_disponibilidad_reasigna_las_tareas_pendientes(self):
        responsable = self.tareas["Judicial"]["responsable_id"]
        respuesta = self.servicio.cambiar_disponibilidad(responsable, False, "Feriado largo", "Jefatura")
        self.assertIn(self.tareas["Judicial"]["id"], respuesta["reasignadas"])
        self.assertNotEqual(self.tareas["Judicial"]["responsable_id"], responsable)
        self.assertEqual(self.tareas["Judicial"]["reasignaciones"], 1)

    def test_reasignar_excluye_al_responsable_anterior(self):
        anterior = self.tareas["Comercial"]["responsable_id"]
        self.servicio.reasignar_tarea(self.tareas["Comercial"]["id"], "Sobrecarga", "Jefatura")
        self.assertNotEqual(self.tareas["Comercial"]["responsable_id"], anterior)


if __name__ == "__main__":
    unittest.main()
