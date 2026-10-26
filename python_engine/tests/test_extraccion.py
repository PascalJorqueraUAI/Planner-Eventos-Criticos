"""Extracción de comprobantes con protección de datos personales."""

import io
import json
import unittest
import urllib.error
from unittest import mock

from controlador.extraccion import (
    ConfigExtraccion,
    extraer_comprobante,
    extraer_local,
    llamar_gemini,
    reidentificar,
    seudonimizar,
)
from tests.utilidades import AHORA, servicio_de_prueba

NOMBRES = ["Carlos Silva Mendoza", "Transportes San Cristóbal SpA"]

TEXTO_COMPLETO = """Hola, transferí $850.000 de la cuota. RUT 16.482.910-K
Comprobante N° TRF-8849102. Carlos Silva Mendoza"""

TEXTO_INCOMPLETO = """Estimados, soy Carlos Silva Mendoza (RUT 16.482.910-K), carlos.silva@empresa.cl,
+56 9 8831 2290. Pagué la cuota desde mi cuenta corriente 0-000-88419-2, adjunto la transferencia."""

ACTIVA = ConfigExtraccion(api_key="clave-de-prueba", modelo="gemini-prueba", autorizado=True)


class Espia:
    """Reemplaza la llamada a Gemini y guarda lo que se le habría enviado."""

    def __init__(self, respuesta=None, error=None):
        self.respuesta = respuesta or {}
        self.error = error
        self.partes = None

    def __call__(self, config, partes):
        self.partes = partes
        if self.error:
            raise self.error
        return self.respuesta

    @property
    def enviado(self) -> str:
        return json.dumps(self.partes, ensure_ascii=False)


def extraer(texto="", imagen=None, confirmacion=False, config=ACTIVA, llamar=None):
    return extraer_comprobante(texto, imagen, "image/jpeg", confirmacion, "Operador", NOMBRES, config, AHORA,
                               llamar=llamar or Espia())


class TestExtraccionLocal(unittest.TestCase):
    def test_extrae_monto_rut_y_operacion(self):
        datos = extraer_local(TEXTO_COMPLETO, NOMBRES)
        self.assertEqual(datos["monto"], 850000)
        self.assertEqual(datos["rut_depositante"], "16.482.910-K")
        self.assertEqual(datos["numero_operacion"], "TRF-8849102")
        self.assertEqual(datos["nombre_depositante"], "Carlos Silva Mendoza")
        self.assertEqual(datos["confianza"], 1.0)

    def test_no_confunde_palabras_con_numero_de_operacion(self):
        self.assertIsNone(extraer_local("Transferencia realizada desde la cuenta empresa")["numero_operacion"])


class TestSeudonimizacion(unittest.TestCase):
    def test_reemplaza_datos_personales_y_conserva_los_del_pago(self):
        texto, mapa = seudonimizar(TEXTO_INCOMPLETO + " Operación TRF-1 por $850.000", NOMBRES)
        for dato in ("16.482.910-K", "carlos.silva@empresa.cl", "+56 9 8831 2290", "0-000-88419-2", "Carlos Silva Mendoza"):
            self.assertNotIn(dato, texto)
        self.assertIn("[RUT_1]", texto)
        self.assertIn("[NOMBRE_1]", texto)
        self.assertIn("$850.000", texto)
        self.assertEqual(len(mapa), 5)

    def test_mismo_dato_mismo_marcador(self):
        texto, mapa = seudonimizar("RUT 16.482.910-K y de nuevo 16.482.910-K", [])
        self.assertEqual(texto.count("[RUT_1]"), 2)
        self.assertEqual(len(mapa), 1)

    def test_reidentificar_devuelve_los_valores_originales(self):
        _, mapa = seudonimizar(TEXTO_INCOMPLETO, NOMBRES)
        datos = reidentificar({"rut_depositante": "[RUT_1]", "nombre_depositante": "[NOMBRE_1]", "monto": 5}, mapa)
        self.assertEqual(datos, {"rut_depositante": "16.482.910-K", "nombre_depositante": "Carlos Silva Mendoza", "monto": 5})


class TestUsoDeGemini(unittest.TestCase):
    def test_sin_autorizacion_nunca_se_envia_aunque_haya_clave(self):
        espia = Espia()
        config = ConfigExtraccion(api_key="clave", modelo="m", autorizado=False)
        datos, registro = extraer(TEXTO_INCOMPLETO, imagen="AAAA", confirmacion=True, config=config, llamar=espia)
        self.assertIsNone(espia.partes)
        self.assertIsNone(registro)
        self.assertEqual(datos["motor_extraccion"], "local")

    def test_si_el_texto_basta_no_se_envia_a_terceros(self):
        espia = Espia()
        datos, registro = extraer(TEXTO_COMPLETO, llamar=espia)
        self.assertIsNone(espia.partes)
        self.assertIsNone(registro)
        self.assertIn("no se envió", datos["motivo"])

    def test_texto_incompleto_se_envia_seudonimizado_y_se_reidentifica(self):
        espia = Espia({"monto": 850000, "numero_operacion": "TRF-77", "rut_depositante": "[RUT_1]",
                       "nombre_depositante": "[NOMBRE_1]", "confianza": 0.9})
        datos, registro = extraer(TEXTO_INCOMPLETO, llamar=espia)
        for dato in ("16.482.910-K", "carlos.silva@empresa.cl", "8831 2290", "88419-2", "Carlos Silva"):
            self.assertNotIn(dato, espia.enviado)
        self.assertEqual(datos["rut_depositante"], "16.482.910-K")
        self.assertEqual(datos["nombre_depositante"], "Carlos Silva Mendoza")
        self.assertEqual(datos["numero_operacion"], "TRF-77")
        self.assertEqual(registro.tipo_entrada, "texto seudonimizado")
        self.assertEqual(registro.resultado, "ok")

    def test_imagen_exige_confirmacion_del_operador(self):
        espia = Espia()
        with self.assertRaises(ValueError):
            extraer(imagen="data:image/jpeg;base64,AAAA", llamar=espia)
        self.assertIsNone(espia.partes)

    def test_imagen_confirmada_se_envia_y_queda_registrada_sin_contenido(self):
        espia = Espia({"monto": 3500000, "numero_operacion": "BCI-TRF-1"})
        datos, registro = extraer(imagen="data:image/jpeg;base64,QUJDRA==", confirmacion=True, llamar=espia)
        self.assertEqual(espia.partes[0]["inlineData"]["data"], "QUJDRA==")
        self.assertEqual(datos["monto"], 3500000)
        self.assertEqual(registro.tipo_entrada, "imagen")
        self.assertEqual(len(registro.hash_entrada), 64)
        self.assertNotIn("QUJDRA==", json.dumps(registro.__dict__))

    def test_si_gemini_falla_vuelve_a_lo_local_y_registra_el_intento(self):
        espia = Espia(error=RuntimeError("Gemini respondió 503"))
        datos, registro = extraer(TEXTO_INCOMPLETO, llamar=espia)
        self.assertEqual(datos["motor_extraccion"], "local")
        self.assertEqual(datos["rut_depositante"], "16.482.910-K")
        self.assertEqual(registro.resultado, "error")

    def test_lo_leido_localmente_prevalece_sobre_el_tercero(self):
        espia = Espia({"monto": 1, "numero_operacion": "OTRA-1", "rut_depositante": "11.111.111-1"})
        datos, _ = extraer(TEXTO_INCOMPLETO, llamar=espia)
        self.assertEqual(datos["rut_depositante"], "16.482.910-K")


class TestClienteGemini(unittest.TestCase):
    """La red se simula: estas pruebas nunca llaman a Google."""

    def test_solicitud_lleva_la_clave_en_header_y_pide_json_con_esquema(self):
        respuesta = io.BytesIO(json.dumps({
            "candidates": [{"content": {"parts": [{"text": json.dumps({"monto": 1000, "numero_operacion": "A-1"})}]}}]
        }).encode())
        with mock.patch("urllib.request.urlopen", return_value=respuesta) as abrir:
            datos = llamar_gemini(ACTIVA, [{"text": "hola"}])
        solicitud = abrir.call_args.args[0]
        self.assertEqual(datos, {"monto": 1000, "numero_operacion": "A-1"})
        self.assertIn("gemini-prueba:generateContent", solicitud.full_url)
        self.assertNotIn("clave-de-prueba", solicitud.full_url)
        self.assertEqual(solicitud.get_header("X-goog-api-key"), "clave-de-prueba")
        cuerpo = json.loads(solicitud.data)
        self.assertEqual(cuerpo["generationConfig"]["responseMimeType"], "application/json")

    def test_error_http_no_arrastra_el_contenido(self):
        error = urllib.error.HTTPError("https://x", 403, "Forbidden", {}, io.BytesIO(b"{}"))
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "Gemini respondió 403"):
                llamar_gemini(ACTIVA, [{"text": "dato"}])


class TestRegistroDeTratamientos(unittest.TestCase):
    def test_el_tratamiento_queda_en_el_repositorio_y_el_historial(self):
        servicio = servicio_de_prueba()
        _, registro = extraer(TEXTO_INCOMPLETO, llamar=Espia({"monto": 1, "numero_operacion": "X-1"}))
        guardado = servicio.registrar_tratamiento(registro.__dict__)
        self.assertEqual(guardado["id"], "TRT-0001")
        self.assertEqual(servicio.estado()["tratamientos"][0]["id"], "TRT-0001")
        self.assertEqual(servicio.repo.listar("historial")[-1]["area"], "Protección de datos")

    def test_la_configuracion_publica_no_expone_la_clave(self):
        self.assertNotIn("clave-de-prueba", json.dumps(ACTIVA.publica()))


if __name__ == "__main__":
    unittest.main()
