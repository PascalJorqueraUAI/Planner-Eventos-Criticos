"""
Prueba de integración REAL con la API de Gemini (usa la red y consume cuota).

No forma parte de `npm test`: se ejecuta a mano con `npm run test:gemini` cuando
hay una GEMINI_API_KEY en el .env. Solo envía datos FICTICIOS (texto inventado y
tests/fixtures/comprobante_ficticio.png), por eso fuerza la autorización del
tratamiento dentro de la prueba sin depender de GEMINI_TRATAMIENTO_AUTORIZADO.
"""

import base64
import json
import os
import sys
import unittest
import urllib.error
import urllib.request

RAIZ_MOTOR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ_MOTOR)

from controlador.extraccion import ConfigExtraccion, extraer_comprobante  # noqa: E402
from entorno import cargar_env  # noqa: E402
from tests.utilidades import AHORA  # noqa: E402

cargar_env()
CONFIG = ConfigExtraccion.desde_entorno()
CONFIG_PRUEBA = ConfigExtraccion(api_key=CONFIG.api_key, modelo=CONFIG.modelo, autorizado=True)
IMAGEN = os.path.join(RAIZ_MOTOR, "tests", "fixtures", "comprobante_ficticio.png")

NOMBRE_FICTICIO = "Persona De Prueba"
TEXTO_FICTICIO = (
    "Hola, soy Persona De Prueba, RUT 11.111.111-1, correo persona.prueba@ejemplo.cl. "
    "Les transferí cuatrocientos treinta y dos mil cien pesos desde mi cuenta corriente 0-000-12345-6 "
    "para la cuota del convenio. Quedo atenta."
)


@unittest.skipUnless(CONFIG.api_key, "Falta GEMINI_API_KEY en el .env (o es el valor de ejemplo)")
class TestGeminiReal(unittest.TestCase):
    def test_el_modelo_configurado_existe(self):
        solicitud = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{CONFIG.modelo}",
            headers={"x-goog-api-key": CONFIG.api_key},
        )
        try:
            with urllib.request.urlopen(solicitud, timeout=20) as respuesta:
                modelo = json.load(respuesta)
        except urllib.error.HTTPError as error:
            self.fail(f"El modelo '{CONFIG.modelo}' no está disponible para esta clave (HTTP {error.code}). "
                      "Revisa GEMINI_MODEL en el .env.")
        self.assertIn("generateContent", modelo.get("supportedGenerationMethods", []))

    def test_texto_se_envia_seudonimizado_y_se_reidentifica(self):
        datos, registro = extraer_comprobante(
            TEXTO_FICTICIO, None, None, False, "Prueba de integración", [NOMBRE_FICTICIO], CONFIG_PRUEBA, AHORA
        )
        self.assertEqual(registro.resultado, "ok", datos["motivo"])
        self.assertEqual(datos["motor_extraccion"], "Gemini")
        for dato in ("11.111.111-1", "persona.prueba@ejemplo.cl", "12345-6", NOMBRE_FICTICIO):
            self.assertNotIn(dato, datos["datos_enviados"])
        self.assertEqual(datos["monto"], 432100)
        self.assertEqual(datos["rut_depositante"], "11.111.111-1")

    def test_imagen_de_comprobante(self):
        with open(IMAGEN, "rb") as archivo:
            imagen = base64.b64encode(archivo.read()).decode()
        datos, registro = extraer_comprobante(
            "", imagen, "image/png", True, "Prueba de integración", [], CONFIG_PRUEBA, AHORA
        )
        self.assertEqual(registro.resultado, "ok", datos["motivo"])
        self.assertEqual(registro.tipo_entrada, "imagen")
        self.assertEqual(datos["monto"], 432100)
        self.assertEqual(datos["numero_operacion"], "DEMO-TRF-555123")
        self.assertEqual(datos["rut_depositante"], "11.111.111-1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
