"""
Punto de entrada del motor Python.

La API REST (server.ts) invoca este script con un comando y le entrega los datos
como JSON por la entrada estándar. La respuesta siempre es JSON por la salida
estándar: {"ok": true, "datos": ...} o {"ok": false, "error": "..."}.

Uso manual:
    py -3 python_engine/cli.py estado
    py -3 python_engine/cli.py escanear
    echo {"tarea_id": "TSK-0001", "resultado": "Pago confirmado"} | py -3 python_engine/cli.py atender-tarea
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controlador.servicio import Servicio  # noqa: E402
from entorno import cargar_env  # noqa: E402
from modelo.repositorio import Repositorio  # noqa: E402

DIRECTORIO_EXPORTACION = os.path.join(os.getcwd(), "exports")


def ejecutar(servicio: Servicio, comando: str, datos: dict):
    usuario = datos.get("usuario") or "Usuario"
    comandos = {
        "estado": lambda: servicio.estado(),
        "caso": lambda: servicio.obtener_caso(datos["caso_id"]),
        "escanear": lambda: servicio.escanear(),
        "actualizar-caso": lambda: servicio.actualizar_caso(datos["caso_id"], datos["cambios"], usuario),
        "ingresar-aviso": lambda: servicio.ingresar_aviso(datos["aviso"], usuario),
        "conciliar-planilla": lambda: servicio.conciliar_planilla(datos["registros"], usuario),
        "crear-caso": lambda: servicio.crear_caso(datos["caso"], datos.get("comprobante"), usuario),
        "importar-casos": lambda: servicio.importar_casos(
            datos["csv"], datos.get("mapeo"), bool(datos.get("solo_validar")), datos.get("usuario") or "Importación de casos"
        ),
        "atender-tarea": lambda: servicio.atender_tarea(datos["tarea_id"], datos["resultado"], datos.get("notas", ""), usuario),
        "reasignar-tarea": lambda: servicio.reasignar_tarea(datos["tarea_id"], datos.get("motivo", ""), usuario),
        "disponibilidad": lambda: servicio.cambiar_disponibilidad(
            datos["colaborador_id"], bool(datos["disponible"]), datos.get("motivo", ""), usuario
        ),
        "registrar-ausencia": lambda: servicio.registrar_ausencia(
            datos["colaborador_id"], datos["desde"], datos["hasta"], datos.get("motivo", ""), usuario
        ),
        "extraer-comprobante": lambda: servicio.extraer_comprobante(datos, usuario),
        "registrar-tratamiento": lambda: servicio.registrar_tratamiento(datos["tratamiento"]),
        "exportar": lambda: servicio.exportar(DIRECTORIO_EXPORTACION),
        "reiniciar": lambda: servicio.reiniciar(datos.get("escenario")),
    }
    if comando not in comandos:
        raise ValueError(f"Comando desconocido: {comando}. Opciones: {', '.join(comandos)}")
    return comandos[comando]()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    cargar_env()
    comando = sys.argv[1] if len(sys.argv) > 1 else "estado"
    entrada = "" if sys.stdin.isatty() else sys.stdin.read()
    try:
        datos = json.loads(entrada) if entrada.strip() else {}
        # La extracción corre fuera de la cola de escritura: no debe inicializar ni escribir el repositorio.
        servicio = Servicio(Repositorio(), inicializar=comando != "extraer-comprobante")
        respuesta = {"ok": True, "datos": ejecutar(servicio, comando, datos)}
        codigo = 0
    except (ValueError, KeyError) as error:
        mensaje = f"Falta el campo {error}" if isinstance(error, KeyError) else str(error)
        respuesta, codigo = {"ok": False, "error": mensaje}, 1
    print(json.dumps(respuesta, ensure_ascii=False))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
