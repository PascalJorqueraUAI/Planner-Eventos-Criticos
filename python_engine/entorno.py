"""
Carga el archivo .env de la raíz del proyecto cuando el motor se ejecuta solo
(por ejemplo, `py -3 python_engine/cli.py` o la prueba de integración con Gemini).

Mismas reglas que dotenv en server.ts: nunca pisa variables que ya existen en el
entorno, y dentro del archivo la última definición de una variable es la que vale.
"""

import os

RUTA_ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def cargar_env(ruta: str = RUTA_ENV) -> None:
    if not os.path.exists(ruta):
        return
    valores = {}
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            nombre, valor = linea.split("=", 1)
            valores[nombre.strip()] = valor.strip().strip('"').strip("'")
    for nombre, valor in valores.items():
        os.environ.setdefault(nombre, valor)
