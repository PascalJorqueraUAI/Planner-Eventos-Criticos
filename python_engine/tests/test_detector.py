import unittest

from controlador import detector
from tests.utilidades import AHORA, servicio_de_prueba, tareas_del_caso


class TestDetectorEventosCriticos(unittest.TestCase):
    def setUp(self):
        self.servicio = servicio_de_prueba()
        self.repo = self.servicio.repo

    def test_carga_inicial_detecta_un_evento_por_regla_del_sandbox(self):
        codigos = sorted((e["caso_id"], e["codigo"]) for e in self.repo.listar("eventos"))
        self.assertEqual(codigos, [
            ("CASO-1052", "EC-01"),
            ("CASO-1053", "EC-02"),
            ("CASO-1054", "EC-04"),
            ("CASO-1056", "EC-05"),
            ("CASO-1057", "EC-03"),
        ])

    def test_comprobante_informado_genera_alerta_judicial_inmediata(self):
        """El caso del auto: un comprobante sin conciliar debe alertar a Judicial al instante."""
        evento, tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        self.assertEqual(set(tareas), {"Comercial", "Judicial"})
        self.assertEqual(tareas["Judicial"]["estado"], "Pendiente")
        self.assertEqual(tareas["Judicial"]["fecha_creacion"], evento["fecha_deteccion"])

    def test_causa_con_apremio_es_critica_con_sla_de_4_horas(self):
        evento, tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        self.assertEqual(evento["prioridad"], "CRITICA")
        self.assertGreater(evento["riesgo_clp"], 0)
        self.assertEqual(evento["riesgo_clp"], sum(p["monto"] for p in evento["riesgo_detalle"]))
        self.assertEqual(tareas["Judicial"]["sla_horas"], 4)

    def test_causa_sin_apremio_no_es_critica(self):
        evento, _ = tareas_del_caso(self.servicio, "CASO-1053", "EC-02")
        self.assertEqual(evento["prioridad"], "ALTA")
        self.assertEqual(evento["riesgo_clp"], 0)
        self.assertEqual(evento["riesgo_detalle"], [])

    def test_escanear_de_nuevo_no_duplica_eventos(self):
        antes = len(self.repo.listar("eventos"))
        self.assertEqual(detector.escanear(self.repo, AHORA), [])
        self.assertEqual(len(self.repo.listar("eventos")), antes)

    def test_nuevo_comprobante_se_asocia_por_rut_y_dispara_ec01(self):
        respuesta = self.servicio.ingresar_aviso(
            {"monto": 3500000, "canal": "Email", "datos_extraidos": {"rut_depositante": "77.194.882-5"}},
            "Ingesta correo",
        )
        self.assertEqual(respuesta["aviso"]["caso_id"], "CASO-1054")
        self.assertEqual([e["codigo"] for e in respuesta["deteccion"]["eventos_nuevos"]], ["EC-01"])

    def test_diligencia_inminente_no_se_duplica_si_hay_aviso_pendiente(self):
        """CASO-1052 tiene diligencia mañana, pero ya está cubierto por EC-01."""
        codigos = [e["codigo"] for e in self.repo.filtrar("eventos", caso_id="CASO-1052")]
        self.assertNotIn("EC-04", codigos)

    def test_pago_confirmado_no_dispara_ec03_mientras_ec01_sigue_abierto(self):
        _, tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        self.servicio.atender_tarea(tareas["Comercial"]["id"], "Pago confirmado", "", "Comercial")
        codigos = [e["codigo"] for e in self.repo.filtrar("eventos", caso_id="CASO-1052")]
        self.assertNotIn("EC-03", codigos)

    def test_pago_confirmado_dispara_ec03_al_cerrar_ec01(self):
        _, tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        self.servicio.atender_tarea(tareas["Comercial"]["id"], "Pago confirmado", "", "Comercial")
        respuesta = self.servicio.atender_tarea(
            tareas["Judicial"]["id"], "Diligencia suspendida preventivamente", "", "Judicial"
        )
        self.assertEqual([e["codigo"] for e in respuesta["deteccion"]["eventos_nuevos"]], ["EC-03"])


if __name__ == "__main__":
    unittest.main()
