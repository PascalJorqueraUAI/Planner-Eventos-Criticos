"""
Cuentas de acceso al sistema (capa Modelo).

Cada colaborador tiene una cuenta; la gerencia general tiene cuentas propias porque
no recibe tareas. El correo institucional se arma con el nombre: los correos que
genera el sistema van a esas direcciones (en el sandbox, solo de forma simulada).

Claves: se guardan como hash scrypt con sal propia. Las cuentas del sandbox no tienen
hash y entran con la clave de demostración (CLAVE_DEMO), solo mientras MODO_DEMO no
sea "no". En operación real cada usuario debe tener su propio hash (ver `hash_clave`).
"""

import hashlib
import hmac
import os
import re
import secrets
import unicodedata
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from modelo.entidades import DOMINIO_CORREO, NIVEL_POR_CARGO, Usuario

GERENCIA_GENERAL = (
    ("Fernando García-Huidobro", "Gerente General"),
    ("Fernando García-Huidobro Hechetle", "Subgerente"),
)

CLAVE_DEMO_POR_DEFECTO = "cobgestion"
CARGOS_RENOMBRADOS = {"Jefe Comercial": "Gerente Comercial", "Jefe Judicial": "Gerente Judicial"}

_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}


def modo_demo() -> bool:
    return (os.environ.get("MODO_DEMO") or "si").strip().lower() not in ("no", "false", "0")


def clave_demo() -> str:
    return os.environ.get("CLAVE_DEMO") or CLAVE_DEMO_POR_DEFECTO


def hash_clave(clave: str) -> str:
    sal = secrets.token_bytes(16)
    digest = hashlib.scrypt(clave.encode("utf-8"), salt=sal, **_SCRYPT)
    return f"scrypt${sal.hex()}${digest.hex()}"


def verificar_clave(usuario: Dict[str, Any], clave: str) -> bool:
    guardado = usuario.get("clave_hash")
    if not guardado:
        return modo_demo() and hmac.compare_digest(clave.encode("utf-8"), clave_demo().encode("utf-8"))
    _, sal, digest = guardado.split("$")
    calculado = hashlib.scrypt(clave.encode("utf-8"), salt=bytes.fromhex(sal), **_SCRYPT)
    return hmac.compare_digest(calculado.hex(), digest)


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def correo_institucional(nombre: str, usados: set) -> str:
    """'Abg. Rodrigo Morales' → rodrigo.morales@cobgestion.cl (con sufijo si ya existe)."""
    partes = [p for p in re.sub(r"^Abg\.\s*", "", nombre).split() if p]
    base = ".".join(re.sub(r"[^a-z0-9-]", "", _sin_tildes(p).lower()) for p in partes)
    correo, n = f"{base}@{DOMINIO_CORREO}", 2
    while correo in usados:
        correo, n = f"{base}{n}@{DOMINIO_CORREO}", n + 1
    usados.add(correo)
    return correo


def crear_usuarios(colaboradores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    usados: set = set()
    usuarios = []
    for nombre, cargo in GERENCIA_GENERAL:
        usuarios.append(Usuario(
            id=f"USR-{len(usuarios) + 1:04d}", nombre=nombre, email=correo_institucional(nombre, usados),
            cargo=cargo, nivel=NIVEL_POR_CARGO[cargo], area="Gerencia",
        ))
    for c in colaboradores:
        usuarios.append(Usuario(
            id=f"USR-{len(usuarios) + 1:04d}", nombre=c["nombre"], email=correo_institucional(c["nombre"], usados),
            cargo=c["cargo"], nivel=NIVEL_POR_CARGO.get(c["cargo"], 3), area=c["area"], colaborador_id=c["id"],
        ))
    return [asdict(u) for u in usuarios]


def asegurar_usuarios(datos: Dict[str, Any]) -> bool:
    """
    Migra un repositorio guardado antes del login: renombra los cargos de jefatura a
    gerencia y crea las cuentas. Devuelve True si cambió algo.
    """
    cambio = False
    for c in datos.get("colaboradores", []):
        if c["cargo"] in CARGOS_RENOMBRADOS:
            c["cargo"] = CARGOS_RENOMBRADOS[c["cargo"]]
            cambio = True
    if not datos.get("usuarios") and datos.get("colaboradores"):
        datos["usuarios"] = crear_usuarios(datos["colaboradores"])
        datos["meta"]["contadores"]["usuarios"] = len(datos["usuarios"])
        cambio = True
    return cambio


def publico(usuario: Dict[str, Any]) -> Dict[str, Any]:
    """Lo que puede salir del motor: nunca el hash de la clave."""
    return {k: v for k, v in usuario.items() if k != "clave_hash"}


def buscar_por_email(usuarios: List[Dict[str, Any]], email: str) -> Optional[Dict[str, Any]]:
    objetivo = (email or "").strip().lower()
    return next((u for u in usuarios if u["email"].lower() == objetivo and u.get("activo", True)), None)
