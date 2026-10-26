"""Asignación automática sin intervención humana: calendario de ausencias y escalamiento por vencimiento."""

import unittest

from modelo.entidades import a_iso
from tests.utilidades import AHORA, Reloj, servicio_de_prueba, tareas_del_caso


class TestCalendarioDeAusencias(unittest.TestCase):
    def setUp(self):
        self.reloj = Reloj()
        self.servicio = servicio_de_prueba(self.reloj)
        self.repo = self.servicio.repo

    def colaborador(self, id_):
        return self.repo.obtener("colaboradores", id_)

    def test_ausencia_vigente_deja_no_disponible_sin_intervencion(self):
        camila = self.colaborador("COL-0001")
        self.assertFalse(camila["disponible"])
        self.assertTrue(camila["no_disponible_por_ausencia"])

    def test_al_terminar_la_ausencia_vuelve_a_estar_disponible(self):
        self.reloj.avanzar(days=2)   # pasa el martes 09:00
        self.servicio.escanear()
        self.assertTrue(self.colaborador("COL-0001")["disponible"])

    def test_no_se_asigna_a_quien_se_ausenta_antes_del_vencimiento(self):
        """Rodrigo sale de vacaciones en 30 h: no puede recibir tareas de 48 o 72 h."""
        for tarea in self.repo.listar("tareas"):
            if tarea["area"] == "Judicial" and tarea["sla_horas"] > 30:
                self.assertNotEqual(tarea["responsable_id"], "COL-0005")
                excluidos = {e["id"]: e["motivo"] for e in tarea["asignacion"]["excluidos"]}
                self.assertIn("ausencia programada", excluidos["COL-0005"])

    def test_programar_ausencia_reasigna_tareas_que_vencen_dentro_de_ella(self):
        _, tareas = tareas_del_caso(self.servicio, "CASO-1053", "EC-02")
        judicial = tareas["Judicial"]
        responsable = judicial["responsable_id"]
        respuesta = self.servicio.registrar_ausencia(
            responsable, a_iso(AHORA.replace(hour=18)), "2026-10-30T09:00:00", "Permiso médico", "RR.HH."
        )
        self.assertIn(judicial["id"], respuesta["reasignadas"])
        self.assertNotEqual(judicial["responsable_id"], responsable)

    def test_marcar_disponible_a_mano_corta_la_ausencia_en_curso(self):
        self.servicio.cambiar_disponibilidad("COL-0001", True, "", "Jefatura")
        self.servicio.escanear()
        self.assertTrue(self.colaborador("COL-0001")["disponible"])

    def test_la_no_disponibilidad_manual_no_la_levanta_el_calendario(self):
        self.servicio.cambiar_disponibilidad("COL-0003", False, "Licencia", "Jefatura")
        self.reloj.avanzar(hours=1)
        self.servicio.escanear()
        self.assertFalse(self.colaborador("COL-0003")["disponible"])


class TestEscalamientoPorVencimiento(unittest.TestCase):
    def setUp(self):
        self.reloj = Reloj()
        self.servicio = servicio_de_prueba(self.reloj)
        self.repo = self.servicio.repo
        _, tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        self.judicial = tareas["Judicial"]          # SLA crítico de 4 h

    def test_antes_del_vencimiento_no_se_mueve(self):
        responsable = self.judicial["responsable_id"]
        self.reloj.avanzar(hours=3)
        self.servicio.escanear()
        self.assertEqual(self.judicial["responsable_id"], responsable)
        self.assertEqual(self.judicial["nivel_escalamiento"], 0)

    def test_vencida_se_reasigna_sola_con_plazo_nuevo(self):
        original = self.judicial["responsable_id"]
        self.reloj.avanzar(hours=4, minutes=5)
        respuesta = self.servicio.escanear()
        self.assertIn(self.judicial["id"], [t["id"] for t in respuesta["deteccion"]["tareas_escaladas"]])
        self.assertEqual(self.judicial["nivel_escalamiento"], 1)
        self.assertNotEqual(self.judicial["responsable_id"], original)
        self.assertEqual(self.judicial["plazo_escalamiento"], "2026-10-26T15:05:00")   # + la mitad del SLA (2 h)

    def test_el_incumplimiento_queda_en_el_historial_del_responsable_original(self):
        original = self.judicial["responsable_id"]
        self.reloj.avanzar(hours=4, minutes=5)
        self.servicio.escanear()
        ultimo = self.repo.filtrar("historial_desempeno", colaborador_id=original)[-1]
        self.assertEqual(ultimo["tarea_id"], self.judicial["id"])
        self.assertFalse(ultimo["cumplio_sla"])

    def test_si_vence_tambien_el_plazo_nuevo_pasa_a_jefatura(self):
        self.reloj.avanzar(hours=4, minutes=5)
        self.servicio.escanear()
        self.reloj.avanzar(hours=2, minutes=5)
        self.servicio.escanear()
        self.assertEqual(self.judicial["nivel_escalamiento"], 2)
        self.assertEqual(self.judicial["responsable_id"], "COL-0008")
        self.assertTrue(self.judicial["asignacion"]["escalada"])

    def test_quien_hereda_y_cumple_su_plazo_suma_un_registro_exitoso(self):
        self.reloj.avanzar(hours=4, minutes=5)
        self.servicio.escanear()
        nuevo = self.judicial["responsable_id"]
        self.reloj.avanzar(hours=1)
        self.servicio.atender_tarea(self.judicial["id"], "Diligencia suspendida preventivamente", "", "Judicial")
        ultimo = self.repo.filtrar("historial_desempeno", colaborador_id=nuevo)[-1]
        self.assertTrue(ultimo["cumplio_sla"])
        self.assertEqual(ultimo["horas_resolucion"], 1.0)


if __name__ == "__main__":
    unittest.main()
