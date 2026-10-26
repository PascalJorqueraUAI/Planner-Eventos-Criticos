import os
import tempfile
import unittest
from unittest import mock

from entorno import cargar_env

CONTENIDO = """# comentario
GEMINI_MODEL="modelo-del-archivo"
VARIABLE_PRUEBA_A='primera'
VARIABLE_PRUEBA_A=segunda
linea sin igual
"""


class TestCargarEnv(unittest.TestCase):
    def cargar(self, entorno_inicial):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8") as archivo:
            archivo.write(CONTENIDO)
        self.addCleanup(os.remove, archivo.name)
        with mock.patch.dict(os.environ, entorno_inicial, clear=True):
            cargar_env(archivo.name)
            return dict(os.environ)

    def test_lee_valores_sin_comillas_y_la_ultima_definicion_gana(self):
        entorno = self.cargar({})
        self.assertEqual(entorno["GEMINI_MODEL"], "modelo-del-archivo")
        self.assertEqual(entorno["VARIABLE_PRUEBA_A"], "segunda")

    def test_no_pisa_variables_que_ya_existen(self):
        entorno = self.cargar({"GEMINI_MODEL": "modelo-del-entorno"})
        self.assertEqual(entorno["GEMINI_MODEL"], "modelo-del-entorno")

    def test_archivo_inexistente_no_falla(self):
        cargar_env(os.path.join(tempfile.gettempdir(), "no-existe-cobgestion.env"))


if __name__ == "__main__":
    unittest.main()
