"""
Métricas del dashboard de trazabilidad.

Todas se calculan a partir del repositorio en el momento de la consulta, por lo
que el dashboard siempre refleja el estado real de los casos.
"""

from collections import Counter
from datetime import datetime
from statistics import mean
from typing import Any, Dict, Optional

from controlador.asignador import carga_actual, perfil_historico
from controlador.seguimiento import esta_vencida
from modelo.entidades import desde_iso
from modelo.repositorio import Repositorio


def _promedio(valores) -> Optional[float]:
    valores = list(valores)
    return round(mean(valores), 1) if valores else None


def calcular_metricas(repo: Repositorio, ahora: datetime) -> Dict[str, Any]:
    casos = repo.listar("casos")
    eventos = repo.listar("eventos")
    tareas = repo.listar("tareas")
    avisos = {a["id"]: a for a in repo.listar("avisos")}

    pendientes = [t for t in tareas if t["estado"] == "Pendiente"]
    atendidas = [t for t in tareas if t["estado"] == "Atendida"]
    vencidas = [t for t in pendientes if esta_vencida(t, ahora)]
    a_tiempo = [t for t in atendidas if desde_iso(t["fecha_atencion"]) <= desde_iso(t["fecha_limite"])]

    # Desfase de información: desde que llega el comprobante hasta que Judicial recibe la alerta.
    # Solo cuenta comprobantes recibidos con el sistema en operación (no los heredados de la carga inicial).
    inicio = repo.datos["meta"].get("cargado_en")
    desfases = [
        (desde_iso(e["fecha_deteccion"]) - desde_iso(avisos[e["aviso_id"]]["fecha_recepcion"])).total_seconds() / 60
        for e in eventos
        if e.get("aviso_id") in avisos
        and (not inicio or avisos[e["aviso_id"]]["fecha_recepcion"] >= inicio)
    ]

    # Riesgo cubierto: eventos con costas en juego cuya tarea judicial se atendió dentro del plazo.
    riesgo_cubierto = 0
    for e in eventos:
        if not e["riesgo_clp"]:
            continue
        judiciales = [t for t in tareas if t["evento_id"] == e["id"] and t["area"] == "Judicial"]
        if judiciales and all(t in a_tiempo for t in judiciales):
            riesgo_cubierto += e["riesgo_clp"]

    colaboradores = []
    for c in repo.listar("colaboradores"):
        propias = [t for t in tareas if t["responsable_id"] == c["id"]]
        colaboradores.append({
            "id": c["id"],
            "nombre": c["nombre"],
            "area": c["area"],
            "cargo": c["cargo"],
            "disponible": c["disponible"],
            "carga": carga_actual(repo, c),
            "capacidad": c["capacidad_max"],
            "pendientes": sum(1 for t in propias if t["estado"] == "Pendiente"),
            "vencidas": sum(1 for t in propias if esta_vencida(t, ahora)),
            "historico": perfil_historico(repo, c["id"]),
        })

    return {
        "total_casos": len(casos),
        "casos_por_estado_judicial": dict(Counter(c["estado_judicial"] for c in casos)),
        "casos_por_estado_comercial": dict(Counter(c["estado_comercial"] for c in casos)),
        "avisos_por_estado": dict(Counter(a["estado"] for a in avisos.values())),
        "eventos_abiertos": sum(1 for e in eventos if e["estado"] == "Abierto"),
        "eventos_criticos_abiertos": sum(1 for e in eventos if e["estado"] == "Abierto" and e["prioridad"] == "CRITICA"),
        "eventos_cerrados": sum(1 for e in eventos if e["estado"] == "Cerrado"),
        "eventos_por_codigo": dict(Counter(e["codigo"] for e in eventos)),
        "tareas_pendientes": len(pendientes),
        "tareas_vencidas": len(vencidas),
        "tareas_atendidas": len(atendidas),
        "cumplimiento_sla_pct": round(100 * len(a_tiempo) / len(atendidas)) if atendidas else None,
        "horas_promedio_atencion": _promedio(
            (desde_iso(t["fecha_atencion"]) - desde_iso(t["fecha_creacion"])).total_seconds() / 3600 for t in atendidas
        ),
        "minutos_promedio_aviso_a_alerta": _promedio(desfases),
        "riesgo_expuesto_clp": sum(e["riesgo_clp"] for e in eventos if e["estado"] == "Abierto"),
        "riesgo_cubierto_clp": riesgo_cubierto,
        "tareas_escaladas": sum(1 for t in pendientes if t.get("asignacion", {}).get("escalada")),
        "tareas_escaladas_por_vencimiento": sum(1 for t in tareas if t.get("nivel_escalamiento", 0) > 0),
        "colaboradores": colaboradores,
    }
