"""
Notificaciones de asignación: aviso dentro del sistema + correo institucional.

Se generan comparando quién tenía cada tarea (y cada caso) antes y después de una
operación, así cubren todos los caminos: asignación automática, reasignación manual,
ausencias, escalamiento por vencimiento y casos nuevos o importados.

Los correos no incluyen datos del deudor (solo códigos de caso y tarea) y en el sandbox
no se envían: quedan en la bandeja simulada, visible en el sistema.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from modelo.entidades import Correo, Notificacion, a_iso, desde_iso
from modelo.repositorio import Repositorio

TITULARES = (("responsable_comercial", "Comercial"), ("responsable_judicial", "Judicial"))
PRIORIDAD_TEXTO = {"CRITICA": "CRÍTICA", "ALTA": "ALTA", "MEDIA": "MEDIA"}


def url_sistema() -> str:
    url = (os.environ.get("APP_URL") or "").strip().rstrip("/")
    return url if url.startswith("http") else f"http://localhost:{os.environ.get('PORT') or 3000}"


def foto(repo: Repositorio) -> Dict[str, Dict[str, Any]]:
    return {
        "tareas": {t["id"]: (t.get("responsable_id"), t.get("nivel_escalamiento", 0)) for t in repo.listar("tareas")},
        "casos": {c["id"]: tuple(c[campo] for campo, _ in TITULARES) for c in repo.listar("casos")},
    }


def _primer_nombre(nombre: str) -> str:
    partes = nombre.replace("Abg.", "").split()
    return partes[0] if partes else nombre


def _plazo(tarea: Dict[str, Any]) -> str:
    vence = desde_iso(tarea.get("plazo_escalamiento") or tarea["fecha_limite"])
    return f"vence el {vence.strftime('%d-%m-%Y %H:%M')}"


class _Emisor:
    def __init__(self, repo: Repositorio, ahora: datetime):
        self.repo = repo
        self.ahora = ahora
        self.por_colaborador = {u["colaborador_id"]: u for u in repo.listar("usuarios") if u.get("colaborador_id")}
        self.creadas: List[Dict[str, Any]] = []

    def gerente(self, area: str) -> Optional[Dict[str, Any]]:
        return next((u for u in self.repo.listar("usuarios") if u["nivel"] == 2 and u["area"] == area), None)

    def emitir(self, usuario: Optional[Dict[str, Any]], tipo: str, titulo: str, mensaje: str, *,
               tarea: Optional[Dict[str, Any]] = None, caso_id: Optional[str] = None,
               con_correo: bool = False, asunto: str = "", cuerpo: str = "") -> None:
        if not usuario:
            return
        prioridad = tarea["prioridad"] if tarea else None
        notificacion = self.repo.insertar("notificaciones", Notificacion(
            id=self.repo.siguiente_id("notificaciones"), usuario_id=usuario["id"], tipo=tipo, titulo=titulo,
            mensaje=mensaje, fecha=a_iso(self.ahora), prioridad=prioridad,
            caso_id=caso_id or (tarea["caso_id"] if tarea else None), tarea_id=tarea["id"] if tarea else None,
        ))
        if con_correo:
            marca = "[CRÍTICA] " if prioridad == "CRITICA" else ""
            correo = self.repo.insertar("correos", Correo(
                id=self.repo.siguiente_id("correos"), para=usuario["email"], para_nombre=usuario["nombre"],
                asunto=f"{marca}{asunto}", cuerpo=_cuerpo(usuario, cuerpo), fecha=a_iso(self.ahora),
                notificacion_id=notificacion["id"],
            ))
            notificacion["correo_id"] = correo["id"]
        self.creadas.append(notificacion)


def _cuerpo(usuario: Dict[str, Any], contenido: str) -> str:
    return (
        f"Hola {_primer_nombre(usuario['nombre'])}:\n\n{contenido}\n\n"
        "Por protección de datos personales (Ley 21.719), este correo no incluye datos del deudor: "
        "revísalos en el sistema.\n\n— Planner de Eventos Críticos · Cobgestion"
    )


def _detalle_tarea(tarea: Dict[str, Any]) -> str:
    return (
        f"Tarea: {tarea['id']} · {tarea['titulo']}\n"
        f"Caso: {tarea['caso_id']}\n"
        f"Prioridad: {tarea['prioridad']}\n"
        f"Plazo: {_plazo(tarea)}\n\n"
        f"Revísala en: {url_sistema()}/#asignacion"
    )


def generar(repo: Repositorio, antes: Dict[str, Dict[str, Any]], ahora: datetime) -> List[Dict[str, Any]]:
    emisor = _Emisor(repo, ahora)
    persona = emisor.por_colaborador.get

    for t in repo.listar("tareas"):
        if t["estado"] != "Pendiente" or not t.get("responsable_id"):
            continue
        anterior, nivel_anterior = antes["tareas"].get(t["id"], (None, 0))
        if t["responsable_id"] == anterior:
            continue
        escalada = t.get("asignacion", {}).get("escalada") or t.get("nivel_escalamiento", 0) == 2
        if anterior is None:
            tipo, accion = ("escalamiento", "Tarea escalada a ti") if escalada else ("asignacion", "Nueva tarea asignada")
            explicacion = ("Ningún colaborador del área podía tomarla, así que quedó a cargo de la gerencia."
                           if escalada else "El sistema te la asignó automáticamente.")
        else:
            tipo, accion = ("escalamiento", "Tarea escalada a ti") if escalada else ("reasignacion", "Se te reasignó una tarea")
            explicacion = ("Venció el plazo y la tarea quedó a cargo de la gerencia." if escalada
                           else "La tarea pasó a ti porque su responsable anterior no podía atenderla a tiempo.")
        emisor.emitir(
            persona(t["responsable_id"]), tipo, accion,
            f"{t['id']} · {t['titulo']} ({t['caso_id']}). Prioridad {PRIORIDAD_TEXTO.get(t['prioridad'], t['prioridad'])}, {_plazo(t)}.",
            tarea=t, con_correo=True, asunto=f"{accion}: {t['id']} · {t['caso_id']}",
            cuerpo=f"{explicacion}\n\n{_detalle_tarea(t)}",
        )
        if anterior:
            emisor.emitir(persona(anterior), "tarea_retirada", "Tarea reasignada a otra persona",
                          f"{t['id']} ({t['caso_id']}) ya no está a tu cargo: no necesitas seguir trabajándola.", tarea=t)
        if nivel_anterior == 0 and t.get("nivel_escalamiento", 0) >= 1:
            gerente = emisor.gerente(t["area"])
            if gerente and gerente.get("colaborador_id") != t["responsable_id"]:
                emisor.emitir(gerente, "vencida", "Tarea vencida en tu área",
                              f"{t['id']} ({t['caso_id']}) venció sin ser atendida y se reasignó automáticamente.", tarea=t)

    for c in repo.listar("casos"):
        previos = antes["casos"].get(c["id"])
        for i, (campo, area) in enumerate(TITULARES):
            if previos is not None and previos[i] == c[campo]:
                continue
            accion = "Eres titular de un caso nuevo" if previos is None else "Eres el nuevo titular de un caso"
            emisor.emitir(
                persona(c[campo]), "titular", accion,
                f"{c['id']} (causa {c['rol_causa']}): quedaste como titular {area.lower()}.",
                caso_id=c["id"], con_correo=True, asunto=f"{accion}: {c['id']}",
                cuerpo=(f"Quedaste como titular {area.lower()} del caso {c['id']} (causa {c['rol_causa']}, {c['tribunal']}).\n\n"
                        f"Revísalo en: {url_sistema()}/#repositorio"),
            )
    return emisor.creadas


def marcar_leidas(repo: Repositorio, usuario_id: str, ids: Optional[List[str]] = None) -> int:
    marcadas = 0
    for n in repo.listar("notificaciones"):
        if n["usuario_id"] == usuario_id and not n["leida"] and (ids is None or n["id"] in ids):
            n["leida"] = True
            marcadas += 1
    return marcadas
