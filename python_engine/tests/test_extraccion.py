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
    sanear,
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


class TestSaneamientoDeLaRespuesta(unittest.TestCase):
    """Casos vistos en respuestas reales de Gemini."""

    def test_rut_con_razonamiento_filtrado_conserva_solo_el_rut(self):
        datos = sanear({"rut_depositante": "11.111.111-1 Barbora/Prueba11111111-1? no, 11.111.111-1. Wait, let's"})
        self.assertEqual(datos["rut_depositante"], "11.111.111-1")

    def test_valores_de_relleno_quedan_vacios(self):
        for relleno in ("NO_DETECTADO", "N/A", "null", "  no detectado. "):
            self.assertIsNone(sanear({"numero_operacion": relleno})["numero_operacion"], relleno)

    def test_numero_de_operacion_debe_parecer_un_codigo(self):
        self.assertEqual(sanear({"numero_operacion": "Comprobante SER-8812903"})["numero_operacion"], "SER-8812903")
        self.assertIsNone(sanear({"numero_operacion": "transferencia"})["numero_operacion"])

    def test_nombre_con_texto_extrano_se_descarta(self):
        self.assertIsNone(sanear({"nombre_depositante": "Persona De Prueba [sic] / 11.111.111-1?"})["nombre_depositante"])
        self.assertEqual(sanear({"nombre_depositante": "Persona De Prueba"})["nombre_depositante"], "Persona De Prueba")

    def test_monto_y_confianza_invalidos(self):
        datos = sanear({"monto": "abc", "confianza": 7})
        self.assertEqual(datos["monto"], 0)
        self.assertIsNone(datos["confianza"])

    def test_la_extraccion_completa_aplica_el_saneamiento(self):
        espia = Espia({"monto": 1000, "numero_operacion": "NO_DETECTADO", "rut_depositante": "[RUT_1] (creo)"})
        datos, _ = extraer("Pagué mil pesos, mi RUT es 16.482.910-K", llamar=espia)
        self.assertIsNone(datos["numero_operacion"])
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

    @staticmethod
    def respuesta_ok(datos=None):
        cuerpo = {"candidates": [{"content": {"parts": [{"text": json.dumps(datos or {"monto": 1})}]}}]}
        return io.BytesIO(json.dumps(cuerpo).encode())

    @staticmethod
    def error_http(codigo, cuerpo=b"{}"):
        return urllib.error.HTTPError("https://x", codigo, "error", {}, io.BytesIO(cuerpo))

    def test_pide_razonamiento_minimo(self):
        with mock.patch("urllib.request.urlopen", return_value=self.respuesta_ok()) as abrir:
            llamar_gemini(ACTIVA, [{"text": "x"}])
        cuerpo = json.loads(abrir.call_args.args[0].data)
        self.assertEqual(cuerpo["generationConfig"]["thinkingConfig"], {"thinkingLevel": "minimal"})

    def test_reintenta_ante_alta_demanda_y_luego_responde(self):
        esperas = []
        efectos = [self.error_http(503), TimeoutError("lento"), self.respuesta_ok({"monto": 7})]
        with mock.patch("urllib.request.urlopen", side_effect=efectos) as abrir:
            datos = llamar_gemini(ACTIVA, [{"text": "x"}], dormir=esperas.append)
        self.assertEqual(datos, {"monto": 7})
        self.assertEqual(abrir.call_count, 3)
        self.assertEqual(esperas, [2.0, 4.0])

    def test_se_rinde_tras_los_intentos_permitidos(self):
        with mock.patch("urllib.request.urlopen", side_effect=[self.error_http(503) for _ in range(3)]):
            with self.assertRaisesRegex(RuntimeError, "503 tras 3 intento"):
                llamar_gemini(ACTIVA, [{"text": "x"}], dormir=lambda _: None)

    def test_no_reintenta_errores_definitivos(self):
        with mock.patch("urllib.request.urlopen", side_effect=[self.error_http(401)]) as abrir:
            with self.assertRaises(RuntimeError):
                llamar_gemini(ACTIVA, [{"text": "x"}], dormir=lambda _: None)
        self.assertEqual(abrir.call_count, 1)

    def test_respeta_el_plazo_total(self):
        instantes = iter([0, 60, 60])   # el primer intento ya consumió 60 s: no cabe otro de 45 s
        with mock.patch("urllib.request.urlopen", side_effect=[TimeoutError("lento"), self.respuesta_ok()]) as abrir:
            with self.assertRaisesRegex(RuntimeError, "tras 1 intento"):
                llamar_gemini(ACTIVA, [{"text": "x"}], dormir=lambda _: None, reloj=lambda: next(instantes))
        self.assertEqual(abrir.call_count, 1)

    def test_cuota_diaria_agotada_no_reintenta_y_explica_cuando_se_renueva(self):
        """Respuesta real de Google al agotar las 20 solicitudes diarias del plan gratuito."""
        cuerpo = json.dumps({"error": {"code": 429, "details": [
            {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
             "violations": [{"quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests"}]},
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "49213s"},
        ]}}).encode()
        with mock.patch("urllib.request.urlopen", side_effect=[self.error_http(429, cuerpo)]) as abrir:
            with self.assertRaisesRegex(RuntimeError, "cuota diaria del plan gratuito .* se renueva en 13 h 40 min"):
                llamar_gemini(ACTIVA, [{"text": "x"}], dormir=lambda _: None)
        self.assertEqual(abrir.call_count, 1)

    def test_limite_por_minuto_espera_lo_que_indica_google(self):
        cuerpo = b'{"error": {"details": [{"@type": "x.RetryInfo", "retryDelay": "7s"}]}}'
        esperas = []
        with mock.patch("urllib.request.urlopen", side_effect=[self.error_http(429, cuerpo), self.respuesta_ok()]):
            llamar_gemini(ACTIVA, [{"text": "x"}], dormir=esperas.append)
        self.assertEqual(esperas, [7.0])

    def test_modelo_sin_ese_nivel_de_razonamiento_se_reintenta_sin_el(self):
        rechazo = self.error_http(400, b'{"error": {"message": "thinking_level minimal is not supported"}}')
        with mock.patch("urllib.request.urlopen", side_effect=[rechazo, self.respuesta_ok()]) as abrir:
            llamar_gemini(ACTIVA, [{"text": "x"}], dormir=lambda _: None)
        segundo = json.loads(abrir.call_args_list[1].args[0].data)
        self.assertNotIn("thinkingConfig", segundo["generationConfig"])

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
