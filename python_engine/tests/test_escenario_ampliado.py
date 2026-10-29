"""
Robustez con el escenario ampliado del sandbox: 24 casos y 14 colaboradores.

Comprueba que el detector encuentra exactamente los eventos esperados (incluidos los
casos que no deben generar eventos) y que el asignador mantiene sus reglas con más
carga: cargo R de la matriz RACI, competencias, capacidad, disponibilidad y ausencias.
También prueba el comportamiento cuando el equipo no alcanza a cubrir todas las tareas.
"""

import copy
import unittest

from controlador.asignador import MATRIZ_RACI, ausencia_en_ventana, carga_actual, fin_ventana
from modelo.datos_iniciales import EVENTOS_ESPERADOS_AMPLIADO
from modelo.entidades import ESTADOS_JUDICIALES_APREMIO, desde_iso
from tests.utilidades import AHORA, Reloj, servicio_de_prueba


class TestDeteccionAmpliada(unittest.TestCase):
    def setUp(self):
        self.servicio = servicio_de_prueba(escenario="ampliado")
        self.repo = self.servicio.repo

    def test_carga_24_casos_y_14_colaboradores(self):
        self.assertEqual(len(self.repo.listar("casos")), 24)
        self.assertEqual(len(self.repo.listar("colaboradores")), 14)

    def test_detecta_exactamente_los_eventos_esperados(self):
        detectados = {}
        for e in self.repo.listar("eventos"):
            detectados.setdefault(e["caso_id"], []).append(e["codigo"])
        for caso_id, esperados in EVENTOS_ESPERADOS_AMPLIADO.items():
            with self.subTest(caso=caso_id):
                self.assertEqual(sorted(detectados.get(caso_id, [])), sorted(esperados))

    def test_cubre_los_cinco_eventos_del_catalogo(self):
        codigos = {e["codigo"] for e in self.repo.listar("eventos")}
        self.assertEqual(codigos, {"EC-01", "EC-02", "EC-03", "EC-04", "EC-05"})

    def test_cada_evento_genera_una_tarea_por_area(self):
        for e in self.repo.listar("eventos"):
            areas = sorted(t["area"] for t in self.repo.filtrar("tareas", evento_id=e["id"]))
            self.assertEqual(areas, ["Comercial", "Judicial"], e["id"])

    def test_causas_con_apremio_quedan_criticas(self):
        casos = {c["id"]: c for c in self.repo.listar("casos")}
        for e in self.repo.listar("eventos"):
            en_apremio = casos[e["caso_id"]]["estado_judicial"] in ESTADOS_JUDICIALES_APREMIO
            self.assertEqual(e["prioridad"] == "CRITICA", en_apremio, e["id"])

    def test_reescanear_no_duplica_eventos(self):
        antes = len(self.repo.listar("eventos"))
        self.servicio.escanear()
        self.assertEqual(len(self.repo.listar("eventos")), antes)


class TestAsignacionAmpliada(unittest.TestCase):
    def setUp(self):
        self.servicio = servicio_de_prueba(escenario="ampliado")
        self.repo = self.servicio.repo
        self.colaboradores = {c["id"]: c for c in self.repo.listar("colaboradores")}

    def test_todas_las_tareas_tienen_responsable_sin_escalar(self):
        for t in self.repo.listar("tareas"):
            self.assertIsNotNone(t["responsable_id"], t["id"])
            self.assertFalse(t["asignacion"]["escalada"], t["id"])

    def test_reglas_de_asignacion(self):
        for t in self.repo.listar("tareas"):
            c = self.colaboradores[t["responsable_id"]]
            cargo_r = next(cargo for cargo, letra in MATRIZ_RACI[t["tipo"]].items() if letra == "R")
            with self.subTest(tarea=t["id"]):
                self.assertEqual(c["cargo"], cargo_r)
                self.assertIn(t["tipo"], c["competencias"])
                self.assertTrue(c["disponible"])
                self.assertIsNone(ausencia_en_ventana(c, AHORA, fin_ventana(t, AHORA)))

    def test_respeta_la_capacidad_de_cada_colaborador(self):
        for c in self.colaboradores.values():
            self.assertLessEqual(carga_actual(self.repo, c), c["capacidad_max"], c["id"])

    def test_licencia_medica_vigente_no_recibe_tareas(self):
        felipe = self.colaboradores["COL-0013"]
        self.assertFalse(felipe["disponible"])
        self.assertEqual(self.repo.filtrar("tareas", responsable_id="COL-0013"), [])

    def test_capacitacion_programada_solo_recibe_tareas_que_vencen_antes(self):
        inicio = desde_iso(self.colaboradores["COL-0011"]["ausencias"][0]["desde"])
        for t in self.repo.filtrar("tareas", responsable_id="COL-0011"):
            self.assertLessEqual(desde_iso(t["fecha_limite"]), inicio, t["id"])


class TestEvolucionEnElTiempo(unittest.TestCase):
    def test_diligencia_que_entra_en_la_ventana_de_72_horas_genera_ec04(self):
        reloj = Reloj()
        servicio = servicio_de_prueba(reloj=reloj, escenario="ampliado")
        self.assertEqual(servicio.repo.filtrar("eventos", caso_id="CASO-1069"), [])
        reloj.avanzar(hours=50)
        servicio.escanear()
        eventos = servicio.repo.filtrar("eventos", caso_id="CASO-1069")
        self.assertEqual([e["codigo"] for e in eventos], ["EC-04"])
        tareas = servicio.repo.filtrar("tareas", evento_id=eventos[0]["id"])
        self.assertTrue(all(t["responsable_id"] for t in tareas))


class TestSaturacion(unittest.TestCase):
    """Más eventos que capacidad: las críticas usan primero los cupos y el exceso se escala."""

    def setUp(self):
        self.servicio = servicio_de_prueba(escenario="ampliado")
        repo = self.servicio.repo
        critico = repo.obtener("casos", "CASO-1058")
        media = repo.obtener("casos", "CASO-1067")
        for i in range(12):
            c = copy.deepcopy(critico)
            c["id"] = f"CASO-{2000 + i}"
            repo.insertar("casos", c)
            repo.insertar("avisos", {
                "id": f"AVP-{3000 + i}", "caso_id": c["id"], "fecha_recepcion": "2026-10-26T08:00:00",
                "monto": 100000, "origen": "Prueba", "canal": "Email", "estado": "informado",
                "datos_extraidos": {}, "observaciones": "",
            })
            m = copy.deepcopy(media)
            m["id"] = f"CASO-{2100 + i}"
            repo.insertar("casos", m)
        self.servicio.escanear()
        self.nuevas = [t for t in repo.listar("tareas") if t["caso_id"] >= "CASO-2000"]

    def test_ninguna_tarea_queda_sin_responsable(self):
        self.assertEqual(len(self.nuevas), 48)
        self.assertTrue(all(t["responsable_id"] for t in self.nuevas))

    def test_los_cupos_libres_se_usan_en_las_tareas_criticas(self):
        def asignadas_a_ejecutivo(prioridad):
            return sum(1 for t in self.nuevas if t["prioridad"] == prioridad and not t["asignacion"]["escalada"])

        self.assertGreater(asignadas_a_ejecutivo("CRITICA"), 0)
        self.assertEqual(asignadas_a_ejecutivo("MEDIA"), 0)

    def test_ejecutivos_no_superan_su_capacidad_y_la_saturacion_se_informa(self):
        repo = self.servicio.repo
        for c in repo.listar("colaboradores"):
            if c["cargo"].startswith("Ejecutivo"):
                self.assertLessEqual(carga_actual(repo, c), c["capacidad_max"], c["id"])
        self.assertGreater(self.servicio.estado()["metricas"]["tareas_sobre_capacidad"], 0)


if __name__ == "__main__":
    unittest.main()
