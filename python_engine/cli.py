"""
Punto de entrada del motor Python.

La API REST (server.ts) invoca este script con un comando y le entrega los datos
como JSON por la entrada estándar. La respuesta siempre es JSON por la salida
estándar: {"ok": true, "datos": ...} o {"ok": false, "error": "..."}.

Cada solicitud de la API trae `actor`: el id del usuario con sesión (o "integracion" para
la clave de servicio). Sin actor, el comando corre como Sistema (uso local y escaneo periódico).
Los permisos se validan en controlador/permisos.py antes de ejecutar el comando.

Uso manual:
    py -3 python_engine/cli.py estado
    py -3 python_engine/cli.py escanear
    echo {"tarea_id": "TSK-0001", "resultado": "Pago confirmado"} | py -3 python_engine/cli.py atender-tarea
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controlador import permisos  # noqa: E402
from controlador.servicio import Servicio  # noqa: E402
from entorno import cargar_env  # noqa: E402
from modelo.repositorio import Repositorio  # noqa: E402

DIRECTORIO_EXPORTACION = os.path.join(os.getcwd(), "exports")


# No requieren sesión: el servidor los usa para iniciarla.
COMANDOS_SIN_SESION = ("login", "usuarios-demo")


def ejecutar(servicio: Servicio, comando: str, datos: dict):
    if comando == "login":
        return servicio.iniciar_sesion(datos.get("email", ""), datos.get("clave", ""))
    if comando == "usuarios-demo":
        return servicio.usuarios_demo()

    actor = permisos.actor_desde(servicio.repo, datos.get("actor"))
    permisos.autorizar(servicio.repo, actor, comando, datos)
    # Una persona firma con su nombre; un sistema externo puede indicar cuál es (CRM, RR.HH.).
    usuario = actor.nombre if actor.tipo == "persona" else (datos.get("usuario") or actor.nombre)
    comandos = {
        "estado": lambda: permisos.vista_para(servicio.repo, actor, servicio.estado()),
        "sesion": lambda: permisos.sesion_de(servicio.repo, actor),
        "caso": lambda: permisos.caso_para(servicio.repo, actor, servicio.obtener_caso(datos["caso_id"])),
        "escanear": lambda: servicio.escanear(),
        "actualizar-caso": lambda: servicio.actualizar_caso(datos["caso_id"], datos["cambios"], usuario),
        "ingresar-aviso": lambda: servicio.ingresar_aviso(datos["aviso"], usuario),
        "conciliar-planilla": lambda: servicio.conciliar_planilla(datos["registros"], usuario),
        "crear-caso": lambda: servicio.crear_caso(datos["caso"], datos.get("comprobante"), usuario),
        "importar-casos": lambda: servicio.importar_casos(
            datos["csv"], datos.get("mapeo"), bool(datos.get("solo_validar")), usuario
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
        "leer-notificaciones": lambda: servicio.leer_notificaciones(actor.id, datos.get("ids")),
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
    except permisos.PermisoDenegado as error:
        respuesta, codigo = {"ok": False, "error": str(error), "prohibido": True}, 1
    except (ValueError, KeyError) as error:
        mensaje = f"Falta el campo {error}" if isinstance(error, KeyError) else str(error)
        respuesta, codigo = {"ok": False, "error": mensaje}, 1
    print(json.dumps(respuesta, ensure_ascii=False))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
