import unittest

from controlador.riesgo import COSTAS_MAXIMAS_CLP, clase_bien, estimar_riesgo
from modelo.entidades import COSTO_INCAUTACION_INDEBIDA_CLP
from tests.utilidades import servicio_de_prueba


def caso(estado_judicial, tipo="Vehículo", descripcion="Automóvil Suzuki Swift 2021", monto_deuda=4_850_000):
    return {"estado_judicial": estado_judicial, "monto_deuda": monto_deuda,
            "bien_garantia": {"tipo": tipo, "descripcion": descripcion}}


class TestRiesgoSegunElCaso(unittest.TestCase):
    def test_caso_del_auto_se_acerca_al_costo_real(self):
        """Calibración: el único costo real conocido es la incautación del auto ($600.000)."""
        riesgo, _ = estimar_riesgo(caso("Orden de incautación vigente"))
        self.assertAlmostEqual(riesgo, COSTO_INCAUTACION_INDEBIDA_CLP, delta=COSTO_INCAUTACION_INDEBIDA_CLP * 0.05)

    def test_desglose_suma_el_total(self):
        riesgo, detalle = estimar_riesgo(caso("Orden de incautación vigente"))
        self.assertEqual(riesgo, sum(p["monto"] for p in detalle))
        self.assertIn("Grúa", [p["concepto"] for p in detalle])

    def test_sin_apremio_no_hay_riesgo(self):
        self.assertEqual(estimar_riesgo(caso("Notificado")), (0, []))

    def test_embargo_cuesta_menos_que_retirar_el_bien(self):
        embargo, detalle = estimar_riesgo(caso("Mandamiento de embargo"))
        retiro, _ = estimar_riesgo(caso("Orden de incautación vigente"))
        self.assertLess(embargo, retiro)
        self.assertNotIn("Grúa", [p["concepto"] for p in detalle])

    def test_vehiculo_pesado_cuesta_mas_que_uno_liviano(self):
        liviano, _ = estimar_riesgo(caso("Diligencia con receptor programada"))
        pesado, _ = estimar_riesgo(caso("Diligencia con receptor programada", descripcion="Camión tolva Mercedes-Benz Actros"))
        self.assertGreater(pesado, liviano)

    def test_camioneta_no_es_vehiculo_pesado(self):
        self.assertEqual(clase_bien({"tipo": "Vehículo", "descripcion": "Camioneta Toyota Hilux 2020"}), "liviano")
        self.assertEqual(clase_bien({"tipo": "Vehículo", "descripcion": "Motocicleta Honda CB500"}), "moto")

    def test_costas_crecen_con_la_deuda_hasta_un_tope(self):
        chica, _ = estimar_riesgo(caso("Mandamiento de embargo", monto_deuda=1_000_000))
        grande, _ = estimar_riesgo(caso("Mandamiento de embargo", monto_deuda=10_000_000))
        enorme, detalle = estimar_riesgo(caso("Mandamiento de embargo", monto_deuda=500_000_000))
        self.assertLess(chica, grande)
        self.assertEqual(detalle[-1]["monto"], COSTAS_MAXIMAS_CLP)

    def test_inmueble_se_embarga_sin_retiro(self):
        _, detalle = estimar_riesgo(caso("Diligencia con receptor programada", tipo="Inmueble", descripcion="Oficina"))
        self.assertIn("Inscripción y alzamiento en el CBR", [p["concepto"] for p in detalle])


class TestRiesgoEnElDetector(unittest.TestCase):
    def test_eventos_criticos_del_sandbox_no_tienen_todos_el_mismo_riesgo(self):
        servicio = servicio_de_prueba(escenario="ampliado")
        riesgos = {e["riesgo_clp"] for e in servicio.repo.listar("eventos") if e["prioridad"] == "CRITICA"}
        self.assertGreater(len(riesgos), 3)


if __name__ == "__main__":
    unittest.main()
