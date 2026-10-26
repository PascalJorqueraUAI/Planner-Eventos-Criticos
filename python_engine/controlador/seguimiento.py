"""
Seguimiento de tareas.

Una tarea queda "Pendiente" hasta que su responsable la marca como "Atendida"
registrando un resultado del catálogo. El resultado se aplica al repositorio
(por ejemplo, el aviso pasa a 'confirmado' o la causa a 'Suspendido preventivo').

Regla de cierre coordinado: un evento crítico solo se cierra cuando TODAS sus
tareas están atendidas. Que Comercial confirme el pago no cierra el evento si
Judicial todavía no suspendió la diligencia.

Automatismos que corren en cada ciclo del detector (sin intervención humana):
  - Calendario de ausencias: quien entra en una ausencia programada queda no
    disponible y sus tareas pendientes se reasignan; al terminar, vuelve solo.
  - Escalamiento por vencimiento: una tarea vencida se reasigna a otra persona con
    un plazo nuevo; si ese plazo también vence, pasa a la jefatura (A de la RACI).
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from controlador.asignador import (
    asignar_a_jefatura,
    asignar_lote,
    ausencia_en_ventana,
    fin_ventana,
    resolver_raci,
)
from controlador.catalogo_eventos import PLANTILLAS_POR_TIPO
from modelo.entidades import RegistroDesempeno, a_iso, desde_iso
from modelo.repositorio import Repositorio

USUARIO_CALENDARIO = "Calendario de ausencias"
USUARIO_ESCALAMIENTO = "Escalamiento automático"


def esta_vencida(tarea: Dict[str, Any], ahora: datetime) -> bool:
    return tarea["estado"] == "Pendiente" and ahora > desde_iso(tarea["fecha_limite"])


def plazo_vigente(tarea: Dict[str, Any]) -> datetime:
    """Plazo del responsable actual: el SLA original o el que le dio el escalamiento."""
    return desde_iso(tarea.get("plazo_escalamiento") or tarea["fecha_limite"])


def ventana_escalamiento(tarea: Dict[str, Any]) -> timedelta:
    """Plazo que recibe quien hereda una tarea vencida: la mitad del SLA, mínimo 1 hora."""
    return timedelta(hours=max(1, tarea["sla_horas"] // 2))


def _registrar_desempeno(repo: Repositorio, tarea: Dict[str, Any], ahora: datetime, cumplio: bool) -> None:
    """El resultado de cada responsable alimenta el historial que usa el asignador."""
    if not tarea.get("responsable_id"):
        return
    inicio = desde_iso(tarea.get("fecha_asignacion") or tarea["fecha_creacion"])
    repo.insertar("historial_desempeno", RegistroDesempeno(
        colaborador_id=tarea["responsable_id"],
        tipo_tarea=tarea["tipo"],
        fecha=a_iso(ahora),
        horas_resolucion=round((ahora - inicio).total_seconds() / 3600, 2),
        cumplio_sla=cumplio,
        tarea_id=tarea["id"],
    ))


# --- Atención de tareas y cierre coordinado ------------------------------------------

def atender_tarea(
    repo: Repositorio,
    tarea_id: str,
    resultado: str,
    notas: str,
    usuario: str,
    ahora: datetime,
) -> Dict[str, Any]:
    tarea = repo.obtener("tareas", tarea_id)
    if tarea["estado"] != "Pendiente":
        raise ValueError(f"La tarea {tarea_id} ya fue atendida")
    plantilla = PLANTILLAS_POR_TIPO[tarea["tipo"]]
    if resultado not in plantilla.resultados:
        raise ValueError(f"Resultado no válido para {tarea['tipo']}: {resultado}")

    evento = repo.obtener("eventos", tarea["evento_id"])
    _aplicar_efectos(repo, plantilla.resultados[resultado], tarea, evento, usuario, ahora)

    cumplio_sla = ahora <= desde_iso(tarea["fecha_limite"])
    _registrar_desempeno(repo, tarea, ahora, cumplio=ahora <= plazo_vigente(tarea))
    repo.actualizar(
        "tareas", tarea_id,
        {
            "estado": "Atendida",
            "resultado": resultado,
            "notas": notas,
            "fecha_atencion": a_iso(ahora),
            "atendida_por": usuario,
        },
        usuario=usuario,
        area=tarea["area"],
        accion="Tarea atendida",
        ahora=ahora,
        detalle=f"{tarea['titulo']}: {resultado}{' (fuera de plazo)' if not cumplio_sla else ''}. {notas}".strip(),
    )

    cerrado, motivo = intentar_cierre(repo, evento, usuario, ahora)
    return {"tarea": tarea, "evento": evento, "evento_cerrado": cerrado, "motivo_cierre": motivo}


def _aplicar_efectos(
    repo: Repositorio,
    efectos: Dict[str, Any],
    tarea: Dict[str, Any],
    evento: Dict[str, Any],
    usuario: str,
    ahora: datetime,
) -> None:
    por_entidad: Dict[str, Dict[str, Any]] = {"caso": {}, "aviso": {}}
    for ruta, valor in efectos.items():
        entidad, campo = ruta.split(".", 1)
        por_entidad[entidad][campo] = valor
    if por_entidad["caso"]:
        repo.actualizar("casos", tarea["caso_id"], por_entidad["caso"], usuario, tarea["area"],
                        f"Actualización por tarea {tarea['id']}", ahora)
    if por_entidad["aviso"] and evento.get("aviso_id"):
        repo.actualizar("avisos", evento["aviso_id"], por_entidad["aviso"], usuario, tarea["area"],
                        f"Actualización por tarea {tarea['id']}", ahora)


def intentar_cierre(repo: Repositorio, evento: Dict[str, Any], usuario: str, ahora: datetime):
    tareas = repo.filtrar("tareas", evento_id=evento["id"])
    pendientes = [t for t in tareas if t["estado"] != "Atendida"]
    if pendientes:
        areas = ", ".join(sorted({t["area"] for t in pendientes}))
        return False, f"El evento sigue abierto: falta la tarea de {areas}."
    repo.actualizar(
        "eventos", evento["id"],
        {"estado": "Cerrado", "fecha_cierre": a_iso(ahora)},
        usuario=usuario,
        area="Sistema",
        accion="Evento cerrado (cierre coordinado)",
        ahora=ahora,
        detalle=f"{evento['nombre']}: todas las áreas atendieron sus tareas.",
    )
    return True, "Todas las áreas atendieron sus tareas."


# --- Reasignación ---------------------------------------------------------------------

def _reasignar_lote(
    repo: Repositorio,
    tareas: List[Dict[str, Any]],
    excluido_id: Optional[str],
    motivo: str,
    usuario: str,
    ahora: datetime,
) -> None:
    anteriores = {t["id"]: t["responsable_id"] for t in tareas}
    asignar_lote(repo, tareas, ahora, usuario=usuario, excluir={t["id"]: excluido_id for t in tareas})
    for t in tareas:
        t["reasignaciones"] = t.get("reasignaciones", 0) + 1
        repo.registrar_historial(
            usuario=usuario,
            area="Sistema",
            accion="Tarea reasignada",
            detalle=f"{t['titulo']}: {anteriores[t['id']]} → {t['responsable_id']}. Motivo: {motivo or 'no informado'}.",
            entidad="Tarea",
            entidad_id=t["id"],
            caso_id=t["caso_id"],
            ahora=ahora,
            cambios={"responsable_id": [anteriores[t["id"]], t["responsable_id"]]},
        )


def reasignar_tarea(repo: Repositorio, tarea_id: str, motivo: str, usuario: str, ahora: datetime) -> Dict[str, Any]:
    tarea = repo.obtener("tareas", tarea_id)
    if tarea["estado"] != "Pendiente":
        raise ValueError("Solo se pueden reasignar tareas pendientes")
    _reasignar_lote(repo, [tarea], tarea["responsable_id"], motivo, usuario, ahora)
    return tarea


# --- Disponibilidad y calendario de ausencias -------------------------------------------

def cambiar_disponibilidad(
    repo: Repositorio,
    colaborador_id: str,
    disponible: bool,
    motivo: str,
    usuario: str,
    ahora: datetime,
    por_ausencia: bool = False,
) -> List[Dict[str, Any]]:
    """
    Marca a un colaborador como (no) disponible. Si deja de estar disponible, sus
    tareas pendientes se reasignan en un solo lote: así un feriado o un permiso no
    deja un comprobante sin revisar.
    """
    colaborador = repo.obtener("colaboradores", colaborador_id)
    cambios: Dict[str, Any] = {
        "disponible": disponible,
        "motivo_no_disponible": "" if disponible else motivo,
        "no_disponible_por_ausencia": por_ausencia and not disponible,
    }
    if disponible and not por_ausencia:
        # Volvió antes: la ausencia en curso termina ahora, para que el calendario no lo desactive de nuevo.
        cambios["ausencias"] = [
            {**a, "hasta": a_iso(ahora)} if desde_iso(a["desde"]) <= ahora < desde_iso(a["hasta"]) else a
            for a in colaborador.get("ausencias", [])
        ]
    repo.actualizar(
        "colaboradores", colaborador_id, cambios,
        usuario=usuario,
        area=colaborador["area"],
        accion="Cambio de disponibilidad",
        ahora=ahora,
        detalle=f"{colaborador['nombre']}: {'disponible' if disponible else 'no disponible — ' + (motivo or 'sin motivo')}.",
    )
    if disponible:
        return []
    pendientes = [t for t in repo.listar("tareas") if t["estado"] == "Pendiente" and t["responsable_id"] == colaborador_id]
    if pendientes:
        _reasignar_lote(repo, pendientes, colaborador_id, f"{colaborador['nombre']} no disponible ({motivo})", usuario, ahora)
    return pendientes


def registrar_ausencia(
    repo: Repositorio,
    colaborador_id: str,
    desde: str,
    hasta: str,
    motivo: str,
    usuario: str,
    ahora: datetime,
) -> List[Dict[str, Any]]:
    """
    Programa una ausencia (vacaciones, permiso, feriado largo). Las tareas pendientes
    del colaborador cuyo plazo cae dentro de la ausencia se reasignan de inmediato,
    sin esperar a que empiece.
    """
    inicio, fin = desde_iso(desde), desde_iso(hasta)
    if fin <= inicio:
        raise ValueError("La ausencia debe terminar después de empezar")
    colaborador = repo.obtener("colaboradores", colaborador_id)
    ausencia = {"desde": desde[:19], "hasta": hasta[:19], "motivo": motivo or "Ausencia programada"}
    repo.actualizar(
        "colaboradores", colaborador_id,
        {"ausencias": colaborador.get("ausencias", []) + [ausencia]},
        usuario=usuario,
        area=colaborador["area"],
        accion="Ausencia programada",
        ahora=ahora,
        detalle=f"{colaborador['nombre']}: {ausencia['motivo']} del {inicio:%d-%m %H:%M} al {fin:%d-%m %H:%M}.",
    )
    afectadas = [
        t for t in repo.listar("tareas")
        if t["estado"] == "Pendiente"
        and t["responsable_id"] == colaborador_id
        and ausencia_en_ventana(colaborador, ahora, fin_ventana(t, ahora))
    ]
    if afectadas:
        _reasignar_lote(repo, afectadas, colaborador_id, f"ausencia programada de {colaborador['nombre']}", usuario, ahora)
    return afectadas


def sincronizar_ausencias(repo: Repositorio, ahora: datetime) -> List[str]:
    """Aplica el calendario: activa o levanta la no disponibilidad según las ausencias vigentes."""
    cambios = []
    for c in repo.listar("colaboradores"):
        vigente = ausencia_en_ventana(c, ahora, ahora + timedelta(seconds=1))
        if vigente and c["disponible"]:
            cambiar_disponibilidad(repo, c["id"], False, vigente["motivo"], USUARIO_CALENDARIO, ahora, por_ausencia=True)
            cambios.append(c["id"])
        elif not vigente and not c["disponible"] and c.get("no_disponible_por_ausencia"):
            cambiar_disponibilidad(repo, c["id"], True, "", USUARIO_CALENDARIO, ahora, por_ausencia=True)
            cambios.append(c["id"])
    return cambios


# --- Escalamiento por vencimiento --------------------------------------------------------

def escalar_vencidas(repo: Repositorio, ahora: datetime) -> List[Dict[str, Any]]:
    """
    Nivel 0 → 1: venció el SLA. Se registra el incumplimiento del responsable y la tarea
                 pasa al mejor colaborador alternativo, con la mitad del SLA como plazo.
    Nivel 1 → 2: también venció ese plazo. La tarea queda en manos de la jefatura (A).
    """
    escaladas = []
    pendientes = [t for t in repo.listar("tareas") if t["estado"] == "Pendiente"]

    primer_nivel = [t for t in pendientes if t.get("nivel_escalamiento", 0) == 0 and esta_vencida(t, ahora)]
    for t in primer_nivel:
        _registrar_desempeno(repo, t, ahora, cumplio=False)
        t["plazo_escalamiento"] = a_iso(ahora + ventana_escalamiento(t))
    # Una por una: cada tarea excluye a su propio responsable anterior.
    for t in primer_nivel:
        _reasignar_lote(repo, [t], t["responsable_id"], "venció el SLA sin ser atendida", USUARIO_ESCALAMIENTO, ahora)
        t["nivel_escalamiento"] = 2 if t["asignacion"].get("escalada") else 1
        escaladas.append(t)

    for t in pendientes:
        if t.get("nivel_escalamiento", 0) == 1 and t not in primer_nivel and ahora > plazo_vigente(t):
            _registrar_desempeno(repo, t, ahora, cumplio=False)
            anterior = t["responsable_id"]
            jefe = asignar_a_jefatura(repo, t, "Escalada a jefatura: venció también el plazo tras la reasignación")
            t.update({
                "nivel_escalamiento": 2,
                "plazo_escalamiento": a_iso(ahora + ventana_escalamiento(t)),
                "fecha_asignacion": a_iso(ahora),
                "reasignaciones": t.get("reasignaciones", 0) + 1,
            })
            t["raci"] = resolver_raci(repo, t, repo.obtener("casos", t["caso_id"]))
            repo.registrar_historial(
                usuario=USUARIO_ESCALAMIENTO,
                area="Sistema",
                accion="Tarea escalada a jefatura",
                detalle=f"{t['titulo']}: {anterior} → {jefe['nombre'] if jefe else 'jefatura'}. Vencieron el SLA y el plazo de reasignación.",
                entidad="Tarea",
                entidad_id=t["id"],
                caso_id=t["caso_id"],
                ahora=ahora,
                cambios={"responsable_id": [anterior, t["responsable_id"]]},
            )
            escaladas.append(t)
    return escaladas
