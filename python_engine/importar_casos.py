"""
Carga de casos desde una exportación del CRM o una planilla de Excel guardada como CSV.

Uso (desde la raíz del proyecto):
    py -3 python_engine/importar_casos.py casos.csv --validar          # solo revisa, no cambia nada
    py -3 python_engine/importar_casos.py casos.csv                    # valida y carga
    py -3 python_engine/importar_casos.py casos.csv --mapeo mapeo.json # columnas con otros nombres

La plantilla y un ejemplo de mapeo están en docs/. Los casos se cargan en el repositorio
del sistema (python_engine/data_store.json) y se ejecuta un ciclo de detección al terminar.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controlador.importador import decodificar  # noqa: E402
from controlador.servicio import Servicio  # noqa: E402
from entorno import cargar_env  # noqa: E402
from modelo.repositorio import Repositorio  # noqa: E402


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Importa casos desde un CSV del CRM o de una planilla.")
    parser.add_argument("archivo", help="Ruta del CSV")
    parser.add_argument("--mapeo", help="JSON {campo_del_sistema: 'Columna del archivo'}")
    parser.add_argument("--validar", action="store_true", help="Solo validar, sin cargar")
    parser.add_argument("--usuario", default="Importación de casos")
    args = parser.parse_args()

    cargar_env()
    with open(args.archivo, "rb") as f:
        contenido = decodificar(f.read())
    mapeo = None
    if args.mapeo:
        with open(args.mapeo, encoding="utf-8") as f:
            mapeo = json.load(f)

    servicio = Servicio(Repositorio())
    resultado = servicio.importar_casos(contenido, mapeo, args.validar, args.usuario)
    r = resultado["importacion"]

    print(f"{'Validación' if args.validar else 'Importación'} de {args.archivo}")
    print(f"  Filas leídas: {r['filas_leidas']} · válidas: {r['validas']} · rechazadas: {len(r['rechazadas'])}")
    if not args.validar:
        print(f"  Nuevas: {len(r['insertadas'])} · actualizadas: {len(r['actualizadas'])} · sin cambios: {len(r['sin_cambios'])}")
        eventos = resultado["deteccion"]["eventos_nuevos"]
        print(f"  Eventos críticos creados al cargar: {len(eventos)}")
        for e in eventos:
            print(f"    {e['id']} {e['codigo']} {e['caso_id']} ({e['prioridad']})")
    if r["columnas_obligatorias_ausentes"]:
        print(f"  Columnas obligatorias que no están en el archivo: {', '.join(r['columnas_obligatorias_ausentes'])}")
    if r["columnas_no_usadas"]:
        print(f"  Columnas ignoradas: {', '.join(r['columnas_no_usadas'])}")
    for x in r["rechazadas"]:
        print(f"  Fila {x['fila']} ({x['caso']}): {'; '.join(x['errores'])}")
    for a in r["advertencias"]:
        print(f"  Advertencia: {a}")
    return 0 if r["validas"] or not r["filas_leidas"] else 1


if __name__ == "__main__":
    sys.exit(main())
