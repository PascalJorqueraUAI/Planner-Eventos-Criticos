"""
Fija la clave propia de un usuario (operación real, con MODO_DEMO="no").

Uso (desde la raíz del proyecto, en el servidor):
    py -3 python_engine/fijar_clave.py nombre.apellido@cobgestion.cl

Pide la clave dos veces sin mostrarla y la guarda como hash scrypt. No hay ruta de la
API para esto a propósito: solo quien administra el servidor puede fijar claves.
"""

import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from entorno import cargar_env  # noqa: E402
from modelo.repositorio import Repositorio  # noqa: E402
from modelo.usuarios import asegurar_usuarios, buscar_por_email, hash_clave  # noqa: E402

LARGO_MINIMO = 10


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Fija la clave propia de un usuario.")
    parser.add_argument("email", help="Correo institucional del usuario")
    args = parser.parse_args()

    cargar_env()
    repo = Repositorio()
    asegurar_usuarios(repo.datos)
    usuario = buscar_por_email(repo.listar("usuarios"), args.email)
    if not usuario:
        print(f"No existe un usuario activo con el correo {args.email}")
        return 1

    clave = getpass.getpass(f"Nueva clave para {usuario['nombre']}: ")
    if len(clave) < LARGO_MINIMO:
        print(f"La clave debe tener al menos {LARGO_MINIMO} caracteres")
        return 1
    if getpass.getpass("Repite la clave: ") != clave:
        print("Las claves no coinciden")
        return 1

    usuario["clave_hash"] = hash_clave(clave)
    repo.guardar()
    print(f"Clave guardada para {usuario['nombre']} ({usuario['email']}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
