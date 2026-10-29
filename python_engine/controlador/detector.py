"""
Detector de eventos críticos.

Recorre el estado actual de todos los casos del repositorio, los compara con el
catálogo de eventos críticos y, cuando una regla se cumple, crea el evento y sus
tareas paralelas (todavía sin responsable: eso lo decide el asignador).

El detector es idempotente: cada evento tiene una `clave` que identifica el hecho
que lo originó, por lo que escanear varias veces no duplica alertas.
"""

from datetime import datetime
from typing import Any, Dict, List

from controlador.catalogo_eventos import (
    CATALOGO,
    Contexto,
    ReglaEvento,
    plazo,
    prioridad_y_riesgo,
    redactar,
)
from modelo.entidades import EventoCritico, Tarea, a_iso
from modelo.repositorio import Repositorio


def escanear(repo: Repositorio, ahora: datetime, usuario: str = "Detector de eventos") -> List[Dict[str, Any]]:
    """Devuelve los eventos nuevos, cada uno con sus tareas en la llave `tareas`."""
    claves_existentes = {e["clave"] for e in repo.listar("eventos")}
    nuevos = []

    for caso in repo.listar("casos"):
        avisos_caso = repo.filtrar("avisos", caso_id=caso["id"])
        for regla in CATALOGO:
            avisos = avisos_caso if regla.ambito == "aviso" else [None]
            for aviso in avisos:
                ctx = Contexto(
                    caso=caso,
                    avisos_caso=avisos_caso,
                    eventos_caso=repo.filtrar("eventos", caso_id=caso["id"]),
                    ahora=ahora,
                    aviso=aviso,
                )
                if not regla.evaluar(ctx):
                    continue
                clave = regla.clave(ctx)
                if clave in claves_existentes:
                    continue
                claves_existentes.add(clave)
                nuevos.append(_crear_evento(repo, regla, ctx, clave, usuario))

    repo.datos["meta"]["ultimo_escaneo"] = a_iso(ahora)
    return nuevos


def _crear_evento(repo: Repositorio, regla: ReglaEvento, ctx: Contexto, clave: str, usuario: str) -> Dict[str, Any]:
    prioridad, riesgo, riesgo_detalle = prioridad_y_riesgo(regla, ctx)
    motivo = f"Regla {regla.codigo}: {regla.condicion}."
    if prioridad == "CRITICA":
        motivo += f" Causa con apremio en curso ({ctx.caso['estado_judicial']}): prioridad CRÍTICA."

    evento = repo.insertar("eventos", EventoCritico(
        id=repo.siguiente_id("eventos"),
        codigo=regla.codigo,
        nombre=regla.nombre,
        caso_id=ctx.caso["id"],
        aviso_id=ctx.aviso["id"] if ctx.aviso else None,
        prioridad=prioridad,
        motivo=motivo,
        clave=clave,
        fecha_deteccion=a_iso(ctx.ahora),
        riesgo_clp=riesgo,
        riesgo_detalle=riesgo_detalle,
    ))
    repo.registrar_historial(
        usuario=usuario,
        area="Sistema",
        accion=f"Evento crítico detectado: {regla.nombre}",
        detalle=motivo,
        entidad="Evento",
        entidad_id=evento["id"],
        caso_id=ctx.caso["id"],
        ahora=ctx.ahora,
    )

    tareas = []
    for plantilla in regla.tareas:
        sla_horas, limite = plazo(plantilla, prioridad, ctx.ahora)
        tareas.append(repo.insertar("tareas", Tarea(
            id=repo.siguiente_id("tareas"),
            evento_id=evento["id"],
            caso_id=ctx.caso["id"],
            tipo=plantilla.tipo,
            area=plantilla.area,
            titulo=plantilla.titulo,
            descripcion=redactar(plantilla.descripcion, ctx),
            prioridad=prioridad,
            sla_horas=sla_horas,
            fecha_creacion=a_iso(ctx.ahora),
            fecha_limite=a_iso(limite),
        )))
    return {**evento, "tareas": tareas}
