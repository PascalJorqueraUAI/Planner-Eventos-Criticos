import unittest

from controlador.trazabilidad import calcular_metricas
from tests.utilidades import Reloj, servicio_de_prueba, tareas_del_caso


class TestConciliacionYMetricas(unittest.TestCase):
    def setUp(self):
        self.reloj = Reloj()
        self.servicio = servicio_de_prueba(self.reloj)
        self.repo = self.servicio.repo

    def test_planilla_confirma_aviso_con_misma_operacion_y_monto(self):
        respuesta = self.servicio.conciliar_planilla(
            [{"rut": "16.482.910-K", "monto": 850000, "codigo_operacion": "TRF-8849102", "mandante": "Forum"}], "Batch"
        )
        self.assertEqual(respuesta["conciliacion"]["confirmados"], ["AVP-0101"])
        self.assertEqual(self.repo.obtener("avisos", "AVP-0101")["estado"], "confirmado")

    def test_planilla_con_otro_monto_deja_el_aviso_observado(self):
        respuesta = self.servicio.conciliar_planilla(
            [{"rut": "16.482.910-K", "monto": 800000, "codigo_operacion": "TRF-8849102", "mandante": "Forum"}], "Batch"
        )
        self.assertEqual(respuesta["conciliacion"]["observados"], ["AVP-0101"])

    def test_pago_en_planilla_sin_aviso_previo_crea_aviso_y_dispara_ec03(self):
        respuesta = self.servicio.conciliar_planilla(
            [{"rut": "15.772.304-1", "monto": 250000, "codigo_operacion": "SER-8812903", "mandante": "Banco Falabella"}], "Batch"
        )
        self.assertEqual(len(respuesta["conciliacion"]["nuevos"]), 1)
        self.assertEqual([e["codigo"] for e in respuesta["deteccion"]["eventos_nuevos"]], ["EC-03"])

    def test_metricas_reflejan_tareas_pendientes_y_vencidas(self):
        self.reloj.avanzar(hours=5)
        m = calcular_metricas(self.repo, self.reloj())
        self.assertEqual(m["tareas_pendientes"], 10)
        self.assertEqual(m["tareas_vencidas"], 3)   # las tres tareas con SLA de 4 h
        self.assertIsNone(m["cumplimiento_sla_pct"])

    def test_riesgo_cubierto_cuando_judicial_actua_a_tiempo(self):
        evento, tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        self.reloj.avanzar(hours=1)
        self.servicio.atender_tarea(tareas["Judicial"]["id"], "Diligencia suspendida preventivamente", "", "Judicial")
        m = calcular_metricas(self.repo, self.reloj())
        self.assertEqual(m["riesgo_cubierto_clp"], evento["riesgo_clp"])
        self.assertEqual(m["cumplimiento_sla_pct"], 100)

    def test_desfase_aviso_alerta_es_cero_para_comprobantes_nuevos(self):
        self.servicio.ingresar_aviso({"caso_id": "CASO-1055", "monto": 100000}, "Ingesta")
        m = calcular_metricas(self.repo, self.reloj())
        self.assertEqual(m["minutos_promedio_aviso_a_alerta"], 0.0)


if __name__ == "__main__":
    unittest.main()
