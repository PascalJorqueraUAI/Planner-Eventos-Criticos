"""
Importador de casos desde una exportación del CRM o una planilla (CSV).

Es la vía de puesta en marcha mientras no exista una integración directa con el CRM:
Cobgestion exporta sus casos a CSV (o guarda su planilla de Excel como CSV) y el sistema
los valida y carga en el repositorio centralizado.

  - Mapeo de columnas configurable: el nombre de cada columna en el archivo de Cobgestion
    se indica en un JSON {campo_del_sistema: "Columna en el archivo"}.
  - Validación fila a fila: campos obligatorios, RUT con dígito verificador, montos, estados
    del catálogo, responsables existentes y del área correcta, fechas.
  - Modo «solo validar» para revisar el archivo sin cambiar nada.
  - Un caso nuevo se inserta; uno existente (mismo id o mismo rol de causa) se actualiza solo
    en los campos editables y cada diferencia queda en el historial.
  - Al terminar, el servicio ejecuta un ciclo de detección: los eventos críticos de los casos
    cargados se crean y asignan en la misma operación.
"""

import csv
import io
import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from controlador.conciliador import normalizar_rut
from modelo.entidades import ESTADOS_COMERCIALES, ESTADOS_JUDICIALES, Caso, a_iso
from modelo.repositorio import Repositorio

# Campos que entiende el importador y su descripción (se usa en la plantilla y la documentación).
CAMPOS = {
    "id": "Id del caso en el sistema (opcional: si viene y existe, el caso se actualiza)",
    "rol_causa": "Rol de la causa (ej. C-1420-2026)",
    "tribunal": "Tribunal",
    "deudor_nombre": "Nombre o razón social del deudor",
    "deudor_rut": "RUT del deudor con dígito verificador",
    "deudor_email": "Correo del deudor",
    "deudor_telefono": "Teléfono del deudor",
    "mandante": "Mandante (banco o financiera)",
    "monto_deuda": "Monto de la deuda en pesos",
    "bien_tipo": "Tipo de bien en garantía (Vehículo, Inmueble, Sin garantía…)",
    "bien_descripcion": "Descripción del bien",
    "bien_patente": "Patente, si es vehículo",
    "estado_comercial": "Estado comercial (ver catálogo)",
    "estado_judicial": "Estado judicial (ver catálogo)",
    "responsable_comercial": "Id o nombre del ejecutivo comercial titular",
    "responsable_judicial": "Id o nombre del ejecutivo judicial titular",
    "fecha_diligencia": "Fecha de la próxima diligencia (opcional)",
}

OBLIGATORIOS_NUEVO = (
    "rol_causa", "tribunal", "deudor_nombre", "deudor_rut", "mandante", "monto_deuda",
    "estado_comercial", "estado_judicial", "responsable_comercial", "responsable_judicial",
)

# Solo estos campos se modifican en un caso que ya existe (igual que la API PATCH /casos/:id).
EDITABLES = ("estado_comercial", "estado_judicial", "fecha_diligencia", "responsable_comercial", "responsable_judicial")

FORMATOS_FECHA = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                  "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%d-%m-%Y", "%d/%m/%Y")

USUARIO_IMPORTACION = "Importación de casos"


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower().strip()


def rut_valido(rut: str) -> bool:
    limpio = normalizar_rut(rut)
    if not limpio or len(limpio) < 2 or not limpio[:-1].isdigit():
        return False
    cuerpo, dv = limpio[:-1], limpio[-1].upper()
    suma, factor = 0, 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    esperado = {11: "0", 10: "K"}.get(11 - suma % 11, str(11 - suma % 11))
    return dv == esperado


def _monto(texto: str) -> int:
    """
    Acepta el formato chileno (1.200.000 o 1.200.000,50) y también el de planillas en inglés
    (1,200,000). Una coma seguida de grupos de tres dígitos es separador de miles, no decimal.
    """
    limpio = re.sub(r"[^\d.,]", "", texto)
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", limpio):
        limpio = limpio.replace(",", "").split(".")[0]
    else:
        limpio = limpio.replace(".", "").split(",")[0]
    if not limpio:
        raise ValueError
    return int(limpio)


def _fecha(texto: str) -> str:
    for formato in FORMATOS_FECHA:
        try:
            return a_iso(datetime.strptime(texto.strip(), formato))
        except ValueError:
            continue
    raise ValueError


def _estado(texto: str, catalogo: Tuple[str, ...]) -> Optional[str]:
    objetivo = _sin_tildes(texto)
    return next((e for e in catalogo if _sin_tildes(e) == objetivo), None)


def leer_csv(contenido: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Detecta el separador (; , o tabulación) y devuelve encabezados y filas."""
    contenido = contenido.lstrip("﻿")
    muestra = contenido[:4096]
    try:
        dialecto = csv.Sniffer().sniff(muestra, delimiters=";,\t")
        separador = dialecto.delimiter
    except csv.Error:
        separador = ";" if muestra.count(";") >= muestra.count(",") else ","
    lector = csv.DictReader(io.StringIO(contenido), delimiter=separador)
    encabezados = [h.strip() for h in (lector.fieldnames or [])]
    filas = []
    for fila in lector:
        filas.append({(k or "").strip(): (v or "").strip() for k, v in fila.items() if k is not None})
    return encabezados, filas


def decodificar(datos: bytes) -> str:
    """Excel en Windows suele guardar CSV en Windows-1252; se prueba UTF-8 primero."""
    for codificacion in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", errors="replace")


def _resolver_colaborador(repo: Repositorio, valor: str, area: str) -> Tuple[Optional[str], Optional[str]]:
    objetivo = _sin_tildes(valor)
    for c in repo.listar("colaboradores"):
        if c["id"].lower() == valor.lower().strip() or _sin_tildes(c["nombre"]) == objetivo:
            if c["area"] != area:
                return None, f"{c['nombre']} pertenece al área {c['area']}, no a {area}"
            return c["id"], None
    return None, f"colaborador desconocido: «{valor}»"


def _validar_fila(repo: Repositorio, fila: Dict[str, str], existente: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str]]:
    errores: List[str] = []
    datos: Dict[str, Any] = {}

    if existente is None:
        for campo in OBLIGATORIOS_NUEVO:
            if not fila.get(campo):
                errores.append(f"falta {campo}")

    if fila.get("deudor_rut") and not rut_valido(fila["deudor_rut"]):
        errores.append(f"RUT inválido: {fila['deudor_rut']}")
    if fila.get("monto_deuda"):
        try:
            datos["monto_deuda"] = _monto(fila["monto_deuda"])
        except ValueError:
            errores.append(f"monto inválido: {fila['monto_deuda']}")
    for campo, catalogo in (("estado_comercial", ESTADOS_COMERCIALES), ("estado_judicial", ESTADOS_JUDICIALES)):
        if fila.get(campo):
            estado = _estado(fila[campo], catalogo)
            if estado:
                datos[campo] = estado
            else:
                errores.append(f"{campo} desconocido: «{fila[campo]}»")
    for campo, area in (("responsable_comercial", "Comercial"), ("responsable_judicial", "Judicial")):
        if fila.get(campo):
            colaborador_id, error = _resolver_colaborador(repo, fila[campo], area)
            if error:
                errores.append(f"{campo}: {error}")
            else:
                datos[campo] = colaborador_id
    if fila.get("fecha_diligencia"):
        try:
            datos["fecha_diligencia"] = _fecha(fila["fecha_diligencia"])
        except ValueError:
            errores.append(f"fecha_diligencia inválida: {fila['fecha_diligencia']} (use AAAA-MM-DD HH:MM o DD-MM-AAAA HH:MM)")
    for campo in ("rol_causa", "tribunal", "deudor_nombre", "deudor_rut", "deudor_email", "deudor_telefono",
                  "mandante", "bien_tipo", "bien_descripcion", "bien_patente"):
        if fila.get(campo):
            datos[campo] = fila[campo]
    return datos, errores


def importar_casos(
    repo: Repositorio,
    contenido: str,
    mapeo: Optional[Dict[str, str]],
    solo_validar: bool,
    usuario: str,
    ahora: datetime,
) -> Dict[str, Any]:
    encabezados, filas_crudas = leer_csv(contenido)
    mapeo_original = mapeo
    mapeo = {campo: columna for campo, columna in (mapeo or {}).items() if campo in CAMPOS}
    columna_de = {campo: mapeo.get(campo, campo) for campo in CAMPOS}
    desconocidos = sorted(k for k in (mapeo_original or {}) if k not in CAMPOS and not k.startswith("_"))
    usadas = {columna_de[c] for c in CAMPOS if columna_de[c] in encabezados}
    no_usadas = [h for h in encabezados if h not in usadas]
    faltantes = [c for c in OBLIGATORIOS_NUEVO if columna_de[c] not in encabezados]

    reporte: Dict[str, Any] = {
        "solo_validar": solo_validar,
        "filas_leidas": len(filas_crudas),
        "validas": 0,
        "insertadas": [],
        "actualizadas": [],
        "sin_cambios": [],
        "rechazadas": [],
        "advertencias": [],
        "columnas_no_usadas": no_usadas,
        "columnas_obligatorias_ausentes": faltantes,
    }
    if desconocidos:
        reporte["advertencias"].append(f"Campos del mapeo que no existen en el sistema: {', '.join(desconocidos)}")

    por_rol = {c["rol_causa"]: c for c in repo.listar("casos")}
    vistos = set()
    preparadas = []
    for numero, cruda in enumerate(filas_crudas, start=2):   # fila 1 = encabezados
        fila = {campo: cruda.get(columna, "") for campo, columna in columna_de.items()}
        if not any(fila.values()):
            continue
        clave = fila.get("id") or fila.get("rol_causa")
        existente = (repo.buscar("casos", fila["id"]) if fila.get("id") else None) or por_rol.get(fila.get("rol_causa"))
        datos, errores = _validar_fila(repo, fila, existente)
        if clave and clave in vistos:
            errores.append(f"duplicado dentro del archivo: {clave}")
        if fila.get("id") and not existente:
            errores.append(f"no existe un caso con id {fila['id']}")
        if errores:
            reporte["rechazadas"].append({"fila": numero, "caso": clave or "—", "errores": errores})
            continue
        vistos.add(clave)
        reporte["validas"] += 1
        preparadas.append((numero, datos, existente))

    if solo_validar:
        return reporte

    for numero, datos, existente in preparadas:
        if existente:
            cambios = {c: datos[c] for c in EDITABLES if c in datos}
            ignorados = [c for c in datos if c not in EDITABLES and c != "id" and datos[c] != _valor_actual(existente, c)]
            if ignorados:
                reporte["advertencias"].append(
                    f"Fila {numero} ({existente['id']}): campos no editables ignorados: {', '.join(ignorados)}")
            antes = dict(existente)
            repo.actualizar("casos", existente["id"], cambios, usuario, "Integración",
                            "Importación de casos desde CRM", ahora)
            destino = "actualizadas" if any(antes.get(c) != existente.get(c) for c in cambios) else "sin_cambios"
            reporte[destino].append(existente["id"])
        else:
            caso = insertar_caso(repo, datos, usuario, ahora, "Caso importado desde CRM",
                                 f"Fila {numero}: causa {datos['rol_causa']} de {datos['deudor_nombre']}.")
            reporte["insertadas"].append(caso["id"])

    repo.registrar_historial(
        usuario=usuario, area="Integración", accion="Importación de casos",
        detalle=(f"{reporte['filas_leidas']} filas leídas: {len(reporte['insertadas'])} nuevas, "
                 f"{len(reporte['actualizadas'])} actualizadas, {len(reporte['sin_cambios'])} sin cambios, "
                 f"{len(reporte['rechazadas'])} rechazadas."),
        entidad="Caso", entidad_id="*", ahora=ahora,
    )
    return reporte


def insertar_caso(repo: Repositorio, datos: Dict[str, Any], usuario: str, ahora: datetime,
                  accion: str, detalle: str) -> Dict[str, Any]:
    """Inserta un caso ya validado (por el importador o por el formulario de nuevo caso)."""
    caso = repo.insertar("casos", Caso(
        id=repo.siguiente_id("casos"),
        rol_causa=datos["rol_causa"],
        tribunal=datos["tribunal"],
        deudor={"nombre": datos["deudor_nombre"], "rut": datos["deudor_rut"],
                "email": datos.get("deudor_email", ""), "telefono": datos.get("deudor_telefono", "")},
        mandante=datos["mandante"],
        monto_deuda=datos["monto_deuda"],
        bien_garantia={"tipo": datos.get("bien_tipo", "Sin garantía"),
                       "descripcion": datos.get("bien_descripcion", ""),
                       **({"patente": datos["bien_patente"]} if datos.get("bien_patente") else {})},
        estado_comercial=datos["estado_comercial"],
        estado_judicial=datos["estado_judicial"],
        responsable_comercial=datos["responsable_comercial"],
        responsable_judicial=datos["responsable_judicial"],
        fecha_creacion=a_iso(ahora),
        ultima_actualizacion=a_iso(ahora),
        fecha_diligencia=datos.get("fecha_diligencia"),
    ))
    repo.registrar_historial(
        usuario=usuario, area="Integración", accion=accion, detalle=detalle,
        entidad="Caso", entidad_id=caso["id"], caso_id=caso["id"], ahora=ahora,
    )
    return caso


def validar_caso_nuevo(repo: Repositorio, campos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida un caso ingresado a mano con las mismas reglas que una fila del importador.
    Lanza ValueError con todos los errores juntos, para mostrarlos de una vez en el formulario.
    """
    fila = {campo: str(campos.get(campo) or "").strip() for campo in CAMPOS if campo != "id"}
    datos, errores = _validar_fila(repo, fila, existente=None)
    if fila.get("rol_causa") and any(c["rol_causa"] == fila["rol_causa"] for c in repo.listar("casos")):
        errores.append(f"ya existe un caso con el rol {fila['rol_causa']}")
    if errores:
        raise ValueError("; ".join(errores))
    return datos


def _valor_actual(caso: Dict[str, Any], campo: str) -> Any:
    if campo.startswith("deudor_"):
        return caso["deudor"].get(campo[len("deudor_"):])
    if campo.startswith("bien_"):
        return caso["bien_garantia"].get(campo[len("bien_"):])
    return caso.get(campo)


def plantilla_csv() -> str:
    """Encabezados de la plantilla de carga (separador ;, como usa Excel en Chile)."""
    return ";".join(CAMPOS) + "\n"
