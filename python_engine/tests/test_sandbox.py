"""Aviso de sandbox desactualizado: los datos guardados son de otro escenario que el configurado."""

import unittest

from controlador.extraccion import ConfigExtraccion
from controlador.servicio import Servicio
from modelo.repositorio import Repositorio
from tests.utilidades import Reloj

SIN_GEMINI = ConfigExtraccion(api_key="", modelo="m", autorizado=False)


def servicio_sobre(repo: Repositorio, escenario: str) -> Servicio:
    """Como hace la CLI: un servicio nuevo sobre los datos ya guardados."""
    return Servicio(repo, reloj=Reloj(), config_extraccion=SIN_GEMINI, escenario=escenario)


class TestInfoSandbox(unittest.TestCase):
    def test_datos_de_una_version_anterior_se_marcan_desactualizados(self):
        repo = Repositorio(ruta=None)
        servicio_sobre(repo, "base")
        del repo.datos["meta"]["escenario"]                  # data_store creado antes del escenario ampliado
        repo.datos["meta"].pop("escenario_explicito", None)
        info = servicio_sobre(repo, "ampliado").estado()["sandbox"]
        self.assertTrue(info["desactualizado"])
        self.assertEqual(info["escenario_cargado"], "base")
        self.assertEqual(info["escenario_configurado"], "ampliado")

    def test_escenario_configurado_cargado_no_avisa(self):
        repo = Repositorio(ruta=None)
        servicio_sobre(repo, "ampliado")
        self.assertFalse(servicio_sobre(repo, "ampliado").estado()["sandbox"]["desactualizado"])

    def test_elegir_otro_escenario_a_proposito_no_avisa(self):
        repo = Repositorio(ruta=None)
        servicio_sobre(repo, "ampliado").reiniciar("base")
        info = servicio_sobre(repo, "ampliado").estado()["sandbox"]
        self.assertEqual(info["escenario_cargado"], "base")
        self.assertFalse(info["desactualizado"])

    def test_reiniciar_sin_elegir_usa_el_configurado(self):
        repo = Repositorio(ruta=None)
        servicio_sobre(repo, "base")
        servicio_sobre(repo, "ampliado").reiniciar()
        self.assertEqual(len(repo.listar("casos")), 24)


if __name__ == "__main__":
    unittest.main()
