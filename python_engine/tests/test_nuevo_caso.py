"""Ingreso manual de un caso: validación, detección inmediata y asignación automática."""

import unittest

from modelo.datos_iniciales import _rut
from tests.utilidades import servicio_de_prueba


def caso(**cambios):
    datos = {
        "rol_causa": "C-9100-2026", "tribunal": "20° Juzgado Civil de Santiago",
        "deudor_nombre": "Deudor De Prueba", "deudor_rut": _rut(14555666), "mandante": "Banco de Prueba",
        "monto_deuda": "5.000.000", "bien_tipo": "Vehículo", "bien_descripcion": "Automóvil de prueba",
        "bien_patente": "ZZ-TT-11", "estado_comercial": "En negociación",
        "estado_judicial": "Orden de incautación vigente",
        "responsable_comercial": "COL-0001", "responsable_judicial": "COL-0005",
    }
    datos.update(cambios)
    return datos


class TestNuevoCaso(unittest.TestCase):
    def setUp(self):
        self.servicio = servicio_de_prueba()
        self.repo = self.servicio.repo

    def test_caso_con_apremio_y_comprobante_genera_ec01_critico_asignado(self):
        r = self.servicio.crear_caso(caso(), {"monto": 850000}, "Operador")
        self.assertEqual(r["caso"]["id"], "CASO-1058")
        self.assertEqual(r["aviso"]["estado"], "informado")
        [evento] = r["eventos_del_caso"]
        self.assertEqual((evento["codigo"], evento["prioridad"]), ("EC-01", "CRITICA"))
        tareas = {t["area"]: t for t in evento["tareas"]}
        self.assertEqual(set(tareas), {"Comercial", "Judicial"})
        self.assertTrue(all(t["responsable"] for t in tareas.values()))
        self.assertEqual(tareas["Judicial"]["sla_horas"], 4)

    def test_titular_no_disponible_queda_excluido(self):
        """Camila (COL-0001) es la titular comercial, pero está con permiso: la tarea va a otra persona."""
        r = self.servicio.crear_caso(caso(), {"monto": 850000}, "Operador")
        comercial = next(t for t in r["eventos_del_caso"][0]["tareas"] if t["area"] == "Comercial")
        self.assertNotEqual(comercial["responsable"], "Camila Valenzuela")
        self.assertIn("Camila Valenzuela", [e["nombre"] for e in comercial["excluidos"]])

    def test_diligencia_inminente_sin_comprobante_genera_ec04(self):
        r = self.servicio.crear_caso(caso(fecha_diligencia="2026-10-28 10:00"), None, "Operador")
        self.assertEqual([e["codigo"] for e in r["eventos_del_caso"]], ["EC-04"])

    def test_caso_sin_apremio_ni_comprobante_no_genera_eventos(self):
        r = self.servicio.crear_caso(caso(estado_judicial="Notificado", bien_tipo="Sin garantía"), None, "Operador")
        self.assertEqual(r["eventos_del_caso"], [])

    def test_errores_se_informan_juntos_y_no_se_crea_nada(self):
        antes = len(self.repo.listar("casos"))
        with self.assertRaises(ValueError) as error:
            self.servicio.crear_caso(caso(deudor_rut="11.111.111-2", responsable_judicial="COL-0001"), None, "Operador")
        self.assertIn("RUT inválido", str(error.exception))
        self.assertIn("pertenece al área Comercial", str(error.exception))
        self.assertEqual(len(self.repo.listar("casos")), antes)

    def test_rol_duplicado_es_rechazado(self):
        with self.assertRaisesRegex(ValueError, "ya existe un caso con el rol C-1420-2026"):
            self.servicio.crear_caso(caso(rol_causa="C-1420-2026"), None, "Operador")

    def test_comprobante_sin_monto_no_deja_el_caso_a_medias(self):
        antes = len(self.repo.listar("casos"))
        with self.assertRaisesRegex(ValueError, "monto del comprobante"):
            self.servicio.crear_caso(caso(), {"monto": 0}, "Operador")
        self.assertEqual(len(self.repo.listar("casos")), antes)


if __name__ == "__main__":
    unittest.main()
