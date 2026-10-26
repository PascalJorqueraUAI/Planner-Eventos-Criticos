import itertools
import unittest

from controlador.asignador import MATRIZ_RACI, asignar_lote, carga_actual, metodo_hungaro
from tests.utilidades import AHORA, servicio_de_prueba, tareas_del_caso


class TestMetodoHungaro(unittest.TestCase):
    def test_encuentra_el_optimo_igual_que_fuerza_bruta(self):
        costos = [
            [0.9, 0.2, 0.7, 0.5],
            [0.3, 0.8, 0.4, 0.6],
            [0.6, 0.5, 0.1, 0.9],
        ]
        solucion = metodo_hungaro(costos)
        costo = sum(costos[i][j] for i, j in enumerate(solucion))
        optimo = min(
            sum(costos[i][j] for i, j in enumerate(perm))
            for perm in itertools.permutations(range(4), 3)
        )
        self.assertAlmostEqual(costo, optimo)
        self.assertEqual(len(set(solucion)), 3)

    def test_matriz_vacia(self):
        self.assertEqual(metodo_hungaro([]), [])


class TestAsignacion(unittest.TestCase):
    def setUp(self):
        self.servicio = servicio_de_prueba()
        self.repo = self.servicio.repo

    def test_titular_no_disponible_queda_excluido_y_se_explica(self):
        """Camila (titular de CASO-1052) está con permiso: el comprobante no puede quedar esperándola."""
        _, tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        comercial = tareas["Comercial"]
        self.assertNotEqual(comercial["responsable_id"], "COL-0001")
        excluidos = {e["id"]: e["motivo"] for e in comercial["asignacion"]["excluidos"]}
        self.assertIn("no disponible", excluidos["COL-0001"])

    def test_solo_asigna_al_cargo_responsable_de_la_matriz_raci(self):
        colaboradores = {c["id"]: c for c in self.repo.listar("colaboradores")}
        for tarea in self.repo.listar("tareas"):
            cargo_r = next(c for c, letra in MATRIZ_RACI[tarea["tipo"]].items() if letra == "R")
            self.assertEqual(colaboradores[tarea["responsable_id"]]["cargo"], cargo_r)

    def test_respeta_competencias(self):
        colaboradores = {c["id"]: c for c in self.repo.listar("colaboradores")}
        for tarea in self.repo.listar("tareas"):
            self.assertIn(tarea["tipo"], colaboradores[tarea["responsable_id"]]["competencias"])

    def test_respeta_la_capacidad_maxima(self):
        for c in self.repo.listar("colaboradores"):
            self.assertLessEqual(carga_actual(self.repo, c), c["capacidad_max"])

    def test_raci_tiene_jefatura_como_aprobador(self):
        _, tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        self.assertEqual(tareas["Judicial"]["raci"]["A"], ["COL-0008"])
        self.assertEqual(tareas["Comercial"]["raci"]["A"], ["COL-0004"])
        # Comercial se consulta en la tarea judicial: es quien está verificando ese pago.
        self.assertEqual(tareas["Judicial"]["raci"]["C"], [tareas["Comercial"]["responsable_id"]])

    def test_sin_colaboradores_factibles_escala_a_jefatura(self):
        for c in self.repo.filtrar("colaboradores", cargo="Ejecutivo Judicial"):
            c["disponible"] = False
        _, tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        judicial = tareas["Judicial"]
        asignar_lote(self.repo, [judicial], AHORA)
        self.assertTrue(judicial["asignacion"]["escalada"])
        self.assertEqual(judicial["responsable_id"], "COL-0008")

    def test_el_historial_cambia_la_decision(self):
        """Con más historial exitoso en el tipo de tarea, sube el puntaje del colaborador."""
        _, tareas = tareas_del_caso(self.servicio, "CASO-1053", "EC-02")
        judicial = tareas["Judicial"]
        antes = {c["id"]: c["puntaje"] for c in judicial["asignacion"]["candidatos"]}
        for _ in range(20):
            self.repo.insertar("historial_desempeno", {
                "colaborador_id": "COL-0007", "tipo_tarea": judicial["tipo"], "fecha": "2026-09-01T10:00:00",
                "horas_resolucion": 3.0, "cumplio_sla": True, "tarea_id": None,
            })
        asignar_lote(self.repo, [judicial], AHORA)
        despues = {c["id"]: c["puntaje"] for c in judicial["asignacion"]["candidatos"]}
        self.assertGreater(despues["COL-0007"], antes["COL-0007"])


if __name__ == "__main__":
    unittest.main()
