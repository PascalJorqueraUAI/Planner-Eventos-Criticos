"""
Extracción de datos de comprobantes de pago, con protección de datos personales
desde el diseño (Ley 19.628 vigente y Ley 21.719, que entra en vigencia el
1 de diciembre de 2026).

La extracción es COMPLEMENTARIA al registro: solo prellena el formulario. Nada se
registra sin que una persona revise y confirme los datos.

Resguardos aplicados:
  - Proporcionalidad: primero se extrae localmente. Gemini (un tercero que procesa
    fuera de Chile) solo se usa si hay una imagen o si el texto no alcanzó.
  - Seudonimización: antes de enviar texto, RUT, correos, teléfonos, cuentas y
    nombres de deudores conocidos se reemplazan por marcadores ([RUT_1]…). La
    respuesta se re-identifica aquí, así el tercero nunca recibe esos datos.
  - Imágenes: no se pueden seudonimizar, por eso exigen confirmación del operador en
    cada envío. El navegador las re-codifica (sin metadatos EXIF/GPS) y nunca se
    almacenan: solo queda su hash.
  - Autorización: Gemini solo se activa con GEMINI_TRATAMIENTO_AUTORIZADO=si, que la
    empresa habilita tras contratar el plan pagado (Google como encargado, con DPA y
    sin uso de los datos para entrenar) y definir la base legal de la transferencia.
  - Responsabilidad: cada envío deja un registro de tratamiento sin el contenido.
"""

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from modelo.entidades import RegistroTratamiento, a_iso

MODELO_POR_DEFECTO = "gemini-3.6-flash"
TIEMPO_MAXIMO_S = 20
FINALIDAD = "Verificación de pagos informados en cobranza judicial y extrajudicial"

CAMPOS = (
    "monto", "banco_origen", "banco_destino", "numero_operacion", "rut_depositante",
    "nombre_depositante", "fecha_hora_operacion", "comentario",
)

PATRON_RUT = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b")
PATRON_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PATRON_TELEFONO = re.compile(r"\+56(?:[\s-]?\d){8,9}")
PATRON_CUENTA = re.compile(r"((?:cuenta(?:\s+corriente)?|cta\.?(?:\s*cte\.?)?)\s*(?:n[°º.]?\s*)?[:#]?\s*)(\d[\d-]{5,})", re.I)
PATRON_MONTO = re.compile(r"\$\s*([\d.]{4,})")
PATRON_OPERACION = re.compile(
    r"(?:operaci[oó]n|comprobante|c[oó]digo[^:\n]*|\bn(?:[°º]|ro\.?))\s*(?:n[°º]\s*)?[:#]?\s*([A-Z0-9]+-[A-Z0-9-]+|\d{5,})",
    re.I,
)
BANCOS = ("Banco de Chile", "Santander", "BancoEstado", "BCI", "Scotiabank", "Itaú", "Falabella", "Servipag", "Caja Vecina")


@dataclass
class ConfigExtraccion:
    api_key: str
    modelo: str
    autorizado: bool

    @classmethod
    def desde_entorno(cls) -> "ConfigExtraccion":
        clave = os.environ.get("GEMINI_API_KEY", "")
        return cls(
            api_key="" if clave in ("", "MY_GEMINI_API_KEY") else clave,
            modelo=os.environ.get("GEMINI_MODEL") or MODELO_POR_DEFECTO,
            autorizado=os.environ.get("GEMINI_TRATAMIENTO_AUTORIZADO", "").strip().lower() in ("si", "sí", "true", "1"),
        )

    @property
    def gemini_activo(self) -> bool:
        return bool(self.api_key) and self.autorizado

    def publica(self) -> Dict[str, Any]:
        """Lo que la interfaz puede saber (nunca la clave)."""
        if self.gemini_activo:
            motivo = "Gemini habilitado: imágenes y textos incompletos se procesan fuera de Chile con resguardos."
        elif self.api_key:
            motivo = "Hay clave de Gemini, pero falta GEMINI_TRATAMIENTO_AUTORIZADO=si: solo extracción local."
        else:
            motivo = "Sin clave de Gemini: solo extracción local de texto."
        return {"gemini_activo": self.gemini_activo, "modelo": self.modelo, "motivo": motivo}


# --- Extracción local (no sale nada del servidor) ---------------------------------------

def extraer_local(texto: str, nombres_conocidos: List[str] = ()) -> Dict[str, Any]:
    monto = PATRON_MONTO.search(texto)
    rut = PATRON_RUT.search(texto)
    operacion = PATRON_OPERACION.search(texto)
    banco = next((b for b in BANCOS if b.lower() in texto.lower()), None)
    nombre = next((n for n in nombres_conocidos if n.lower() in texto.lower()), None)
    datos = {
        "monto": int(monto.group(1).replace(".", "")) if monto else 0,
        "banco_origen": banco,
        "numero_operacion": operacion.group(1) if operacion else None,
        "rut_depositante": rut.group(0) if rut else None,
        "nombre_depositante": nombre,
    }
    claves = ("monto", "numero_operacion", "rut_depositante")
    datos["confianza"] = round(sum(1 for k in claves if datos[k]) / len(claves), 2)
    return datos


def es_suficiente(datos: Dict[str, Any]) -> bool:
    """Con monto, operación y RUT el comprobante se puede conciliar: no hace falta un tercero."""
    return bool(datos.get("monto") and datos.get("numero_operacion") and datos.get("rut_depositante"))


# --- Seudonimización ---------------------------------------------------------------------

def seudonimizar(texto: str, nombres_conocidos: List[str] = ()) -> Tuple[str, Dict[str, str]]:
    """Reemplaza datos personales por marcadores estables. Devuelve el texto y el mapa marcador → valor."""
    mapa: Dict[str, str] = {}
    inverso: Dict[Tuple[str, str], str] = {}

    def marcador(tipo: str, valor: str) -> str:
        clave = (tipo, valor.lower())
        if clave not in inverso:
            n = sum(1 for t, _ in inverso if t == tipo) + 1
            inverso[clave] = f"[{tipo}_{n}]"
            mapa[inverso[clave]] = valor
        return inverso[clave]

    texto = PATRON_CORREO.sub(lambda m: marcador("CORREO", m.group(0)), texto)
    texto = PATRON_RUT.sub(lambda m: marcador("RUT", m.group(0)), texto)
    texto = PATRON_TELEFONO.sub(lambda m: marcador("TELEFONO", m.group(0)), texto)
    texto = PATRON_CUENTA.sub(lambda m: m.group(1) + marcador("CUENTA", m.group(2)), texto)
    for nombre in sorted(nombres_conocidos, key=len, reverse=True):
        if len(nombre) < 6:
            continue
        texto = re.sub(re.escape(nombre), lambda m: marcador("NOMBRE", m.group(0)), texto, flags=re.I)
    return texto, mapa


def reidentificar(datos: Dict[str, Any], mapa: Dict[str, str]) -> Dict[str, Any]:
    resultado = {}
    for campo, valor in datos.items():
        if isinstance(valor, str):
            for marca, original in mapa.items():
                valor = valor.replace(marca, original)
        resultado[campo] = valor
    return resultado


# --- Cliente Gemini (REST, solo biblioteca estándar) -----------------------------------------

PROMPT = """Eres el extractor de comprobantes de pago de una empresa de cobranza en Chile.
Extrae SOLO los datos del pago: monto (entero en pesos, sin puntos ni signo $), banco_origen,
banco_destino, numero_operacion, rut_depositante, nombre_depositante, fecha_hora_operacion y
comentario (glosa de la transferencia). No describas la imagen ni agregues otros datos personales.
Los marcadores entre corchetes, como [RUT_1] o [NOMBRE_1], reemplazan datos personales:
cópialos tal cual en el campo que corresponda y no intentes deducir el dato real.
Indica en confianza (0 a 1) qué tan seguro estás de la extracción.

Texto recibido: {texto}"""

ESQUEMA = {
    "type": "OBJECT",
    "properties": {
        **{campo: {"type": "STRING"} for campo in CAMPOS if campo != "monto"},
        "monto": {"type": "INTEGER"},
        "confianza": {"type": "NUMBER"},
    },
    "required": ["monto", "numero_operacion"],
}

LlamadaGemini = Callable[[ConfigExtraccion, List[Dict[str, Any]]], Dict[str, Any]]


def llamar_gemini(config: ConfigExtraccion, partes: List[Dict[str, Any]]) -> Dict[str, Any]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.modelo}:generateContent"
    cuerpo = {
        "contents": [{"role": "user", "parts": partes}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": ESQUEMA},
    }
    solicitud = urllib.request.Request(
        url,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": config.api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(solicitud, timeout=TIEMPO_MAXIMO_S) as respuesta:
            datos = json.load(respuesta)
    except urllib.error.HTTPError as error:
        # El cuerpo de error de Google no contiene el comprobante; el de la solicitud no se registra nunca.
        raise RuntimeError(f"Gemini respondió {error.code}") from None
    texto = datos["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(texto)


# --- Orquestación ----------------------------------------------------------------------------

def _registro(usuario: str, config: ConfigExtraccion, tipo: str, categorias: List[str],
              medidas: List[str], huella: str, resultado: str, ahora: datetime) -> RegistroTratamiento:
    return RegistroTratamiento(
        id="",                       # lo asigna el repositorio al guardarlo
        timestamp=a_iso(ahora),
        usuario=usuario,
        finalidad=FINALIDAD,
        proveedor="Google LLC — Gemini API (encargado del tratamiento)",
        modelo=config.modelo,
        ubicacion="Fuera de Chile (transferencia internacional)",
        tipo_entrada=tipo,
        categorias_datos=categorias,
        medidas=medidas,
        hash_entrada=huella,
        resultado=resultado,
    )


def extraer_comprobante(
    texto: str,
    imagen_base64: Optional[str],
    mime_type: Optional[str],
    confirmacion_operador: bool,
    usuario: str,
    nombres_conocidos: List[str],
    config: ConfigExtraccion,
    ahora: datetime,
    llamar: LlamadaGemini = llamar_gemini,
) -> Tuple[Dict[str, Any], Optional[RegistroTratamiento]]:
    """Devuelve (datos para prellenar el formulario, registro de tratamiento si hubo envío a un tercero)."""
    texto = texto or ""
    imagen = (imagen_base64 or "").split(",", 1)[-1] or None
    huella = hashlib.sha256((imagen or texto).encode("utf-8")).hexdigest()
    local = extraer_local(texto, nombres_conocidos)
    base = {**local, "hash_comprobante": huella, "datos_enviados": None}

    if not config.gemini_activo:
        motivo = (
            "Gemini no está habilitado: nada salió del servidor. Completa a mano lo que falte."
            if not imagen
            else "Gemini no está habilitado: la imagen no se procesó; completa los datos a mano."
        )
        return {**base, "motor_extraccion": "local", "motivo": motivo}, None
    if not imagen and es_suficiente(local):
        return {**base, "motor_extraccion": "local",
                "motivo": "El texto bastó para extraer monto, RUT y operación: no se envió a terceros."}, None
    if imagen and not confirmacion_operador:
        raise ValueError("Para enviar una imagen a Gemini, el operador debe confirmar que contiene solo el comprobante.")

    texto_seudonimo, mapa = seudonimizar(texto, nombres_conocidos)
    partes: List[Dict[str, Any]] = []
    medidas = ["Extracción local previa", "Plan pagado: sin uso para entrenamiento", "Sin almacenamiento del comprobante (solo hash)"]
    categorias = ["Datos financieros (monto, banco, operación)"]
    if imagen:
        partes.append({"inlineData": {"mimeType": mime_type or "image/jpeg", "data": imagen}})
        medidas += ["Imagen sin metadatos EXIF/GPS", "Confirmación del operador"]
        categorias += ["Imagen del comprobante (puede incluir nombre y RUT)"]
    if mapa:
        medidas.append(f"Seudonimización del texto ({len(mapa)} dato(s) reemplazado(s))")
    partes.append({"text": PROMPT.format(texto=texto_seudonimo or "(sin texto, analiza la imagen)")})
    tipo = "imagen" if imagen else "texto seudonimizado"

    try:
        crudo = llamar(config, partes)
    except Exception as error:  # noqa: BLE001 — cualquier falla del tercero vuelve a la extracción local
        registro = _registro(usuario, config, tipo, categorias, medidas, huella, "error", ahora)
        return {**base, "motor_extraccion": "local", "datos_enviados": texto_seudonimo,
                "motivo": f"Gemini no respondió ({error}); se usó la extracción local."}, registro

    remoto = reidentificar({k: crudo.get(k) for k in CAMPOS}, mapa)
    # Lo que se leyó localmente manda: no depende de la interpretación de un tercero.
    combinado = {k: local.get(k) or remoto.get(k) for k in CAMPOS}
    combinado["monto"] = int(combinado.get("monto") or 0)
    registro = _registro(usuario, config, tipo, categorias, medidas, huella, "ok", ahora)
    return {
        **combinado,
        "confianza": crudo.get("confianza"),
        "hash_comprobante": huella,
        "datos_enviados": texto_seudonimo,
        "motor_extraccion": "Gemini",
        "motivo": "Procesado por Gemini con los resguardos del registro de tratamiento. Revisa los datos antes de registrar.",
    }, registro
