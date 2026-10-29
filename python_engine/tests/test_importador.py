"""Importador de casos desde una exportación del CRM o una planilla (CSV)."""

import unittest

from controlador.importador import CAMPOS, _monto, decodificar, leer_csv, plantilla_csv, rut_valido
from modelo.datos_iniciales import _rut
from tests.utilidades import servicio_de_prueba

ENCABEZADO = ";".join(CAMPOS)


def fila(**valores) -> str:
    base = {
        "rol_causa": "C-9001-2026", "tribunal": "15° Juzgado Civil de Santiago",
        "deudor_nombre": "Deudor de Prueba", "deudor_rut": _rut(14555666), "mandante": "Banco de Prueba",
        "monto_deuda": "$3.500.000", "bien_tipo": "Vehículo", "bien_descripcion": "Automóvil de prueba",
        "bien_patente": "ZZ-ZZ-99", "estado_comercial": "En negociación", "estado_judicial": "Notificado",
        "responsable_comercial": "Ignacio Rivas", "responsable_judicial": "COL-0006",
    }
    base.update(valores)
    return ";".join(base.get(c, "") for c in CAMPOS)


def csv_de(*filas: str) -> str:
    return "\n".join([ENCABEZADO, *filas]) + "\n"


class TestValidaciones(unittest.TestCase):
    def test_rut_valido(self):
        self.assertTrue(rut_valido("14.555.666-K"))
        self.assertTrue(rut_valido("14555666k"))
        self.assertTrue(rut_valido(_rut(17223344)))
        self.assertFalse(rut_valido("14.555.666-1"))
        self.assertFalse(rut_valido("abc"))

    def test_detecta_el_separador(self):
        encabezados, filas = leer_csv("rol,tribunal\nC-1,Juzgado\n")
        self.assertEqual(encabezados, ["rol", "tribunal"])
        self.assertEqual(filas[0]["tribunal"], "Juzgado")

    def test_decodifica_csv_guardado_por_excel_en_windows(self):
        self.assertEqual(decodificar("Notificación;Peña".encode("cp1252")), "Notificación;Peña")

    def test_plantilla_tiene_todos_los_campos(self):
        self.assertEqual(plantilla_csv().strip().split(";"), list(CAMPOS))


class TestImportacion(unittest.TestCase):
    def setUp(self):
        self.servicio = servicio_de_prueba()
        self.repo = self.servicio.repo
        self.casos_iniciales = len(self.repo.listar("casos"))

    def test_inserta_caso_nuevo_y_lo_deja_en_el_historial(self):
        r = self.servicio.importar_casos(csv_de(fila()))["importacion"]
        self.assertEqual(len(r["insertadas"]), 1)
        caso = self.repo.obtener("casos", r["insertadas"][0])
        self.assertEqual(caso["monto_deuda"], 3500000)
        self.assertEqual(caso["responsable_comercial"], "COL-0002")
        self.assertEqual(caso["bien_garantia"]["patente"], "ZZ-ZZ-99")
        self.assertTrue(any(h["accion"] == "Caso importado desde CRM" and h["caso_id"] == caso["id"]
                            for h in self.repo.listar("historial")))

    def test_caso_importado_con_diligencia_inminente_genera_evento_asignado(self):
        r = self.servicio.importar_casos(csv_de(fila(
            estado_judicial="Orden de incautación vigente", fecha_diligencia="28-10-2026 09:00")))
        eventos = r["deteccion"]["eventos_nuevos"]
        self.assertEqual([e["codigo"] for e in eventos], ["EC-04"])
        self.assertEqual(eventos[0]["prioridad"], "CRITICA")
        tareas = self.repo.filtrar("tareas", evento_id=eventos[0]["id"])
        self.assertEqual(sorted(t["area"] for t in tareas), ["Comercial", "Judicial"])
        self.assertTrue(all(t["responsable_id"] for t in tareas))

    def test_actualiza_caso_existente_por_rol_y_normaliza_estados(self):
        r = self.servicio.importar_casos(csv_de(fila(
            rol_causa="C-1102-2026", estado_judicial="orden de incautacion vigente",
            estado_comercial="en negociacion", fecha_diligencia="2026-10-27 10:00")))
        importacion = r["importacion"]
        self.assertEqual(importacion["actualizadas"], ["CASO-1055"])
        caso = self.repo.obtener("casos", "CASO-1055")
        self.assertEqual(caso["estado_judicial"], "Orden de incautación vigente")
        self.assertEqual(caso["fecha_diligencia"], "2026-10-27T10:00:00")
        self.assertEqual(len(self.repo.listar("casos")), self.casos_iniciales)
        cambio = next(h for h in self.repo.listar("historial") if h["accion"] == "Importación de casos desde CRM")
        self.assertEqual(cambio["cambios"]["estado_judicial"], ["Notificado", "Orden de incautación vigente"])
        self.assertIn("EC-04", [e["codigo"] for e in r["deteccion"]["eventos_nuevos"]])
        # El nombre del deudor no es editable por importación: se advierte y no se cambia.
        self.assertTrue(any("no editables" in a for a in importacion["advertencias"]))
        self.assertEqual(caso["deudor"]["nombre"], "Gonzalo Patricio Alarcón")

    def test_rechaza_filas_invalidas_y_carga_las_validas(self):
        r = self.servicio.importar_casos(csv_de(
            fila(),
            fila(rol_causa="C-9002-2026", deudor_rut="11.111.111-2"),
            fila(rol_causa="C-9003-2026", estado_judicial="Archivado"),
            fila(rol_causa="C-9004-2026", tribunal=""),
            fila(rol_causa="C-9005-2026", responsable_judicial="Ignacio Rivas"),
            fila(rol_causa="C-9006-2026", monto_deuda="sin monto"),
            fila(),
        ))["importacion"]
        self.assertEqual(r["filas_leidas"], 7)
        self.assertEqual(len(r["insertadas"]), 1)
        errores = {x["caso"]: " ".join(x["errores"]) for x in r["rechazadas"]}
        self.assertIn("RUT inválido", errores["C-9002-2026"])
        self.assertIn("estado_judicial desconocido", errores["C-9003-2026"])
        self.assertIn("falta tribunal", errores["C-9004-2026"])
        self.assertIn("pertenece al área Comercial", errores["C-9005-2026"])
        self.assertIn("monto inválido", errores["C-9006-2026"])
        self.assertIn("duplicado", errores["C-9001-2026"])

    def test_solo_validar_no_modifica_el_repositorio(self):
        historial = len(self.repo.listar("historial"))
        r = self.servicio.importar_casos(csv_de(fila(), fila(rol_causa="C-1102-2026", estado_judicial="Mandamiento de embargo")),
                                         solo_validar=True)["importacion"]
        self.assertEqual(r["validas"], 2)
        self.assertEqual(r["insertadas"], [])
        self.assertEqual(len(self.repo.listar("casos")), self.casos_iniciales)
        self.assertEqual(len(self.repo.listar("historial")), historial)
        self.assertEqual(self.repo.obtener("casos", "CASO-1055")["estado_judicial"], "Notificado")

    def test_mapeo_de_columnas_del_crm(self):
        contenido = (
            "ROL,Juzgado,Cliente,RUT Cliente,Banco,Deuda,Etapa Comercial,Etapa Judicial,Ejecutivo,Abogado,Otra columna\n"
            f"C-9100-2026,1° Juzgado Civil de Talca,Cliente CRM,{_rut(15666777).replace(',', '')},Banco CRM,1200000,"
            "Acuerdo vigente,Notificado,COL-0003,COL-0007,x\n"
        )
        mapeo = {"rol_causa": "ROL", "tribunal": "Juzgado", "deudor_nombre": "Cliente", "deudor_rut": "RUT Cliente",
                 "mandante": "Banco", "monto_deuda": "Deuda", "estado_comercial": "Etapa Comercial",
                 "estado_judicial": "Etapa Judicial", "responsable_comercial": "Ejecutivo", "responsable_judicial": "Abogado"}
        r = self.servicio.importar_casos(contenido, mapeo)["importacion"]
        self.assertEqual(len(r["insertadas"]), 1, r["rechazadas"])
        self.assertEqual(r["columnas_no_usadas"], ["Otra columna"])
        self.assertEqual(self.repo.obtener("casos", r["insertadas"][0])["deudor"]["nombre"], "Cliente CRM")

    def test_informa_columnas_obligatorias_ausentes(self):
        r = self.servicio.importar_casos("rol_causa;tribunal\nC-1;Juzgado\n", solo_validar=True)["importacion"]
        self.assertIn("deudor_rut", r["columnas_obligatorias_ausentes"])
        self.assertEqual(r["validas"], 0)


class TestFormatosDeMonto(unittest.TestCase):
    def test_formatos_chileno_e_ingles(self):
        casos = {
            "$3.500.000": 3500000,
            "3500000": 3500000,
            "1.200.000,50": 1200000,
            "1,200,000": 1200000,          # planilla en formato inglés: antes se leía como 1
            "$1,200,000.75": 1200000,
            "950,5": 950,
        }
        for texto, esperado in casos.items():
            self.assertEqual(_monto(texto), esperado, texto)

    def test_sin_digitos_es_invalido(self):
        with self.assertRaises(ValueError):
            _monto("sin monto")


if __name__ == "__main__":
    unittest.main()
