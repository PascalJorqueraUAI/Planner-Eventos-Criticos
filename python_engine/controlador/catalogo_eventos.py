"""
Catálogo de eventos críticos.

Un evento crítico es un cambio o antecedente relevante de un caso que requiere
que otra área revise su gestión, tome una decisión o actúe dentro de un plazo.
Cada regla del catálogo define:
  - la condición que se evalúa sobre el estado actual del caso (y su aviso de pago),
  - las tareas paralelas que se crean para cada área, con su SLA,
  - los resultados posibles de cada tarea y su efecto sobre el repositorio.

Agregar un evento nuevo al sistema es agregar una regla a CATALOGO.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from controlador.riesgo import estimar_riesgo
from modelo.entidades import (
    ESTADOS_JUDICIALES_APREMIO,
    ESTADOS_JUDICIALES_CERRADOS,
    desde_iso,
)

HORAS_DILIGENCIA_INMINENTE = 72


@dataclass
class Contexto:
    """Lo que una regla puede mirar al evaluarse."""
    caso: Dict[str, Any]
    avisos_caso: List[Dict[str, Any]]
    eventos_caso: List[Dict[str, Any]]
    ahora: datetime
    aviso: Optional[Dict[str, Any]] = None

    @property
    def en_apremio(self) -> bool:
        return self.caso["estado_judicial"] in ESTADOS_JUDICIALES_APREMIO

    @property
    def causa_cerrada(self) -> bool:
        return self.caso["estado_judicial"] in ESTADOS_JUDICIALES_CERRADOS

    @property
    def horas_a_diligencia(self) -> Optional[float]:
        if not self.caso.get("fecha_diligencia"):
            return None
        return (desde_iso(self.caso["fecha_diligencia"]) - self.ahora).total_seconds() / 3600

    def evento_abierto_del_aviso(self) -> bool:
        return any(
            e["estado"] == "Abierto" and e.get("aviso_id") == self.aviso["id"]
            for e in self.eventos_caso
        )


@dataclass(frozen=True)
class PlantillaTarea:
    tipo: str
    area: str
    titulo: str
    descripcion: str                # admite {rol}, {tribunal}, {monto}, {bien}, {mandante}, {deudor}, {diligencia}
    sla_horas: int
    sla_horas_critica: int
    resultados: Dict[str, Dict[str, Any]]   # resultado -> {"caso.campo" | "aviso.campo": nuevo valor}


@dataclass(frozen=True)
class ReglaEvento:
    codigo: str
    nombre: str
    descripcion: str
    condicion: str                  # versión legible de `evaluar`, se muestra en la interfaz
    ambito: str                     # "aviso": se evalúa por cada aviso del caso | "caso": una vez por caso
    evaluar: Callable[[Contexto], bool]
    clave: Callable[[Contexto], str]
    tareas: Tuple[PlantillaTarea, ...]
    prioridad_base: str = "ALTA"


def prioridad_y_riesgo(regla: ReglaEvento, ctx: Contexto) -> Tuple[str, int, List[Dict[str, Any]]]:
    """Una causa con apremio en curso eleva el evento a CRÍTICO: hay costas en juego, estimadas según el caso."""
    if ctx.en_apremio:
        return ("CRITICA", *estimar_riesgo(ctx.caso))
    return regla.prioridad_base, 0, []


def _clave_aviso(codigo: str) -> Callable[[Contexto], str]:
    return lambda ctx: f"{codigo}:{ctx.caso['id']}:{ctx.aviso['id']}"


def _hay_aviso_sin_conciliar(ctx: Contexto) -> bool:
    return any(a["estado"] in ("informado", "observado") for a in ctx.avisos_caso)


CATALOGO: Tuple[ReglaEvento, ...] = (
    ReglaEvento(
        codigo="EC-01",
        nombre="Pago informado pendiente de verificación",
        descripcion=(
            "Llegó un comprobante o aviso de pago que aún no está conciliado. "
            "Judicial debe revisarlo de inmediato, sin esperar la conciliación de Comercial."
        ),
        condicion="Aviso en estado 'informado' y la causa no está terminada",
        ambito="aviso",
        evaluar=lambda ctx: ctx.aviso["estado"] == "informado" and ctx.caso["estado_judicial"] != "Terminado por pago",
        clave=_clave_aviso("EC-01"),
        tareas=(
            PlantillaTarea(
                tipo="VERIFICAR_PAGO",
                area="Comercial",
                titulo="Verificar comprobante contra cartola o planilla del mandante",
                descripcion="Verificar el pago informado de {monto} del deudor {deudor} contra la cartola bancaria o la planilla de {mandante}.",
                sla_horas=24,
                sla_horas_critica=8,
                resultados={
                    "Pago confirmado": {"aviso.estado": "confirmado"},
                    "Pago observado (diferencias o antecedentes pendientes)": {"aviso.estado": "observado"},
                },
            ),
            PlantillaTarea(
                tipo="EVALUAR_SUSPENSION",
                area="Judicial",
                titulo="Revisar la causa y evaluar suspensión de apremios",
                descripcion="Se informó un pago de {monto} en la causa {rol} ({tribunal}). Revisar gestiones pendientes sobre {bien}{diligencia} y decidir si se suspenden.",
                sla_horas=24,
                sla_horas_critica=4,
                resultados={
                    "Diligencia suspendida preventivamente": {"caso.estado_judicial": "Suspendido preventivo por aviso de pago"},
                    "Mantener curso de la causa": {},
                },
            ),
        ),
    ),
    ReglaEvento(
        codigo="EC-02",
        nombre="Pago observado con diferencias",
        descripcion="El pago no cuadra con la fuente (monto distinto, comprobante ilegible o antecedentes pendientes).",
        condicion="Aviso en estado 'observado'",
        ambito="aviso",
        evaluar=lambda ctx: ctx.aviso["estado"] == "observado",
        clave=_clave_aviso("EC-02"),
        tareas=(
            PlantillaTarea(
                tipo="ACLARAR_DISCREPANCIA",
                area="Comercial",
                titulo="Aclarar la diferencia del pago con el deudor o el mandante",
                descripcion="El aviso de {monto} del deudor {deudor} quedó observado. Aclarar la diferencia con el deudor o con {mandante}.",
                sla_horas=48,
                sla_horas_critica=24,
                resultados={
                    "Diferencia aclarada, pago confirmado": {"aviso.estado": "confirmado"},
                    "Pago no corresponde / rechazado": {},
                },
            ),
            PlantillaTarea(
                tipo="EVALUAR_CURSO_CAUSA",
                area="Judicial",
                titulo="Evaluar el curso de la causa mientras el pago está observado",
                descripcion="El pago de la causa {rol} quedó observado. Decidir si se mantiene la suspensión o se reanuda la tramitación.",
                sla_horas=48,
                sla_horas_critica=24,
                resultados={
                    "Mantener suspensión": {},
                    "Reanudar tramitación": {"caso.estado_judicial": "En tramitación"},
                },
            ),
        ),
    ),
    ReglaEvento(
        codigo="EC-03",
        nombre="Pago confirmado con causa activa",
        descripcion="El pago ya está verificado, pero la causa sigue viva en tribunales. Judicial debe suspender formalmente o terminar la causa.",
        condicion="Aviso 'confirmado', causa no suspendida formalmente ni terminada, y sin otro evento abierto por ese aviso",
        ambito="aviso",
        evaluar=lambda ctx: (
            ctx.aviso["estado"] == "confirmado"
            and not ctx.causa_cerrada
            and not ctx.evento_abierto_del_aviso()
        ),
        clave=_clave_aviso("EC-03"),
        tareas=(
            PlantillaTarea(
                tipo="FORMALIZAR_SUSPENSION_TERMINO",
                area="Judicial",
                titulo="Presentar suspensión formal o término de la causa",
                descripcion="Pago de {monto} confirmado en la causa {rol} ({tribunal}). Presentar el escrito que corresponda.",
                sla_horas=48,
                sla_horas_critica=24,
                resultados={
                    "Suspensión formal presentada en tribunal": {"caso.estado_judicial": "Suspendido formalmente en tribunal"},
                    "Término de causa por pago total": {
                        "caso.estado_judicial": "Terminado por pago",
                        "caso.estado_comercial": "Pagado",
                    },
                },
            ),
            PlantillaTarea(
                tipo="REGISTRAR_PAGO_CRM",
                area="Comercial",
                titulo="Registrar el pago conciliado en el CRM",
                descripcion="Registrar el pago confirmado de {monto} del deudor {deudor} y actualizar el saldo con {mandante}.",
                sla_horas=24,
                sla_horas_critica=24,
                resultados={
                    "Pago registrado en CRM": {},
                },
            ),
        ),
    ),
    ReglaEvento(
        codigo="EC-04",
        nombre="Diligencia inminente con negociación abierta",
        descripcion="Hay una diligencia de apremio en las próximas 72 horas mientras Comercial negocia con el deudor.",
        condicion=f"Causa con apremio, diligencia en ≤ {HORAS_DILIGENCIA_INMINENTE} h, negociación o acuerdo vigente y sin avisos pendientes",
        ambito="caso",
        evaluar=lambda ctx: (
            ctx.en_apremio
            and ctx.horas_a_diligencia is not None
            and 0 <= ctx.horas_a_diligencia <= HORAS_DILIGENCIA_INMINENTE
            and ctx.caso["estado_comercial"] in ("En negociación", "Acuerdo vigente")
            and not _hay_aviso_sin_conciliar(ctx)
        ),
        clave=lambda ctx: f"EC-04:{ctx.caso['id']}:{ctx.caso['fecha_diligencia']}",
        tareas=(
            PlantillaTarea(
                tipo="CONFIRMAR_DILIGENCIA",
                area="Judicial",
                titulo="Confirmar o reprogramar la diligencia con el receptor",
                descripcion="La diligencia de la causa {rol} sobre {bien} está fijada{diligencia}. Coordinar con el receptor según el estado de la negociación.",
                sla_horas=8,
                sla_horas_critica=4,
                resultados={
                    "Diligencia confirmada con receptor": {},
                    "Diligencia reprogramada": {"caso.fecha_diligencia": None},
                },
            ),
            PlantillaTarea(
                tipo="CONTACTAR_DEUDOR",
                area="Comercial",
                titulo="Contactar al deudor antes de la diligencia",
                descripcion="Contactar a {deudor} para confirmar si pagará antes de la diligencia{diligencia}.",
                sla_horas=8,
                sla_horas_critica=4,
                resultados={
                    "Deudor contactado, compromiso de pago": {"caso.estado_comercial": "Acuerdo vigente"},
                    "Sin contacto": {"caso.estado_comercial": "Sin contacto"},
                },
            ),
        ),
    ),
    ReglaEvento(
        codigo="EC-05",
        nombre="Convenio incumplido con causa suspendida",
        descripcion="El deudor incumplió el convenio y la causa está suspendida: hay que decidir si se reactiva.",
        condicion="Estado comercial 'Convenio incumplido' y causa suspendida",
        ambito="caso",
        evaluar=lambda ctx: (
            ctx.caso["estado_comercial"] == "Convenio incumplido"
            and ctx.caso["estado_judicial"].startswith("Suspendido")
        ),
        clave=lambda ctx: f"EC-05:{ctx.caso['id']}:{ctx.caso['estado_judicial']}",
        prioridad_base="MEDIA",
        tareas=(
            PlantillaTarea(
                tipo="REACTIVAR_CAUSA",
                area="Judicial",
                titulo="Evaluar reactivación de la causa",
                descripcion="El convenio de {deudor} fue incumplido. Evaluar reactivar la causa {rol} ({tribunal}).",
                sla_horas=72,
                sla_horas_critica=48,
                resultados={
                    "Tramitación reanudada": {"caso.estado_judicial": "En tramitación"},
                    "Mantener suspensión por repactación": {},
                },
            ),
            PlantillaTarea(
                tipo="GESTIONAR_REPACTACION",
                area="Comercial",
                titulo="Gestionar repactación con el deudor",
                descripcion="Intentar repactar la deuda de {deudor} con {mandante} antes de reactivar la causa.",
                sla_horas=48,
                sla_horas_critica=24,
                resultados={
                    "Repactación acordada": {"caso.estado_comercial": "Acuerdo vigente"},
                    "Sin acuerdo": {},
                },
            ),
        ),
    ),
)

PLANTILLAS_POR_TIPO: Dict[str, PlantillaTarea] = {
    plantilla.tipo: plantilla for regla in CATALOGO for plantilla in regla.tareas
}


def redactar(texto: str, ctx: Contexto) -> str:
    caso = ctx.caso
    bien = caso["bien_garantia"]
    descripcion_bien = bien["descripcion"] + (f" (patente {bien['patente']})" if bien.get("patente") else "")
    diligencia = ""
    if caso.get("fecha_diligencia"):
        diligencia = f" para el {desde_iso(caso['fecha_diligencia']).strftime('%d-%m-%Y %H:%M')}"
    monto = ctx.aviso["monto"] if ctx.aviso else caso["monto_deuda"]
    return texto.format(
        rol=caso["rol_causa"],
        tribunal=caso["tribunal"],
        monto=f"${monto:,.0f}".replace(",", "."),
        bien=descripcion_bien,
        mandante=caso["mandante"],
        deudor=caso["deudor"]["nombre"],
        diligencia=diligencia,
    )


def plazo(plantilla: PlantillaTarea, prioridad: str, ahora: datetime) -> Tuple[int, datetime]:
    horas = plantilla.sla_horas_critica if prioridad == "CRITICA" else plantilla.sla_horas
    return horas, ahora + timedelta(hours=horas)


def catalogo_serializado() -> List[Dict[str, Any]]:
    """Versión del catálogo para la Vista (sin las funciones)."""
    return [
        {
            "codigo": r.codigo,
            "nombre": r.nombre,
            "descripcion": r.descripcion,
            "condicion": r.condicion,
            "ambito": r.ambito,
            "prioridad_base": r.prioridad_base,
            "tareas": [
                {
                    "tipo": p.tipo,
                    "area": p.area,
                    "titulo": p.titulo,
                    "sla_horas": p.sla_horas,
                    "sla_horas_critica": p.sla_horas_critica,
                    "resultados": list(p.resultados.keys()),
                }
                for p in r.tareas
            ],
        }
        for r in CATALOGO
    ]
