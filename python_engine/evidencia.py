"""
Paquete de evidencia del prototipo (`npm run evidencia`).

Genera la carpeta evidencia/<fecha_hora>/ con material verificable para la presentación:

  README.md             Resumen con las cifras principales y cómo se obtuvieron.
  deteccion.md          Escenario ampliado: eventos esperados frente a detectados, caso por caso.
  recorrido_demo.md     El caso del auto paso a paso (detección, asignación, cierre coordinado,
                        comprobante nuevo, aviso del CRM, ausencia y vencimiento).
  simulacion.md         Una semana simulada de operación con llegadas de avisos y cambios del CRM.
  metricas.json         Todas las cifras en formato máquina.
  pruebas.txt           Salida completa de las pruebas unitarias.
  exportaciones/        Hojas del repositorio al final del recorrido, en CSV para Excel.
  checklist_capturas.md Capturas de la interfaz que conviene sacar a mano.

Todo corre sobre un repositorio en memoria con los datos ficticios del sandbox: no modifica
python_engine/data_store.json y nunca llama a Gemini ni a otro servicio externo.
"""

import argparse
import io
import json
import os
import random
import sys
import unittest
from collections import Counter
from datetime import datetime, timedelta
from statistics import mean, median
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controlador.catalogo_eventos import PLANTILLAS_POR_TIPO  # noqa: E402
from controlador.extraccion import ConfigExtraccion  # noqa: E402
from controlador.servicio import Servicio  # noqa: E402
from modelo.datos_iniciales import EVENTOS_ESPERADOS_AMPLIADO  # noqa: E402
from modelo.entidades import ESTADOS_JUDICIALES_APREMIO, a_iso, desde_iso  # noqa: E402
from modelo.repositorio import Repositorio  # noqa: E402

DIRECTORIO_MOTOR = os.path.dirname(os.path.abspath(__file__))
DIRECTORIO_RAIZ = os.path.dirname(DIRECTORIO_MOTOR)

# Línea base del diagnóstico (datos entregados por Cobgestion; no se simulan).
LINEA_BASE = {
    "mediana_horas_deteccion_conflictos": 12.4,
    "p90_horas_deteccion_conflictos": 65,
    "diferencias_fecha_ultima_gestion": 51,
    "costo_incautacion_indebida_clp": 600000,
}


class Reloj:
    """Reloj controlable: permite avanzar el tiempo en el recorrido y en la simulación."""

    def __init__(self, inicio: datetime):
        self.momento = inicio

    def __call__(self) -> datetime:
        return self.momento

    def avanzar(self, **kw) -> None:
        self.momento += timedelta(**kw)

    def ir_a(self, momento: datetime) -> None:
        if momento > self.momento:
            self.momento = momento


def nuevo_servicio(reloj: Reloj, escenario: str = "ampliado") -> Servicio:
    sin_gemini = ConfigExtraccion(api_key="", modelo="sin-modelo", autorizado=False)
    return Servicio(Repositorio(ruta=None), reloj=reloj, config_extraccion=sin_gemini, escenario=escenario)


def _pesos(monto: int) -> str:
    return f"${monto:,.0f}".replace(",", ".")


def _n(valor: Any) -> str:
    """Número con coma decimal, como en las slides."""
    if valor is None:
        return "—"
    if isinstance(valor, float):
        return (f"{valor:.1f}".rstrip("0").rstrip(".") if valor % 1 else f"{valor:.0f}").replace(".", ",")
    return str(valor)


def _pct(parte: int, total: int) -> Optional[float]:
    return round(100 * parte / total, 1) if total else None


def _nombres(repo: Repositorio) -> Dict[str, str]:
    return {c["id"]: c["nombre"] for c in repo.listar("colaboradores")}


# --- 1. Detección con el escenario ampliado ------------------------------------------

def verificar_deteccion(inicio: datetime) -> Dict[str, Any]:
    servicio = nuevo_servicio(Reloj(inicio))
    repo = servicio.repo
    casos = {c["id"]: c for c in repo.listar("casos")}
    eventos = repo.listar("eventos")
    tareas = repo.listar("tareas")
    nombres = _nombres(repo)

    detectados: Dict[str, List[str]] = {}
    for e in eventos:
        detectados.setdefault(e["caso_id"], []).append(e["codigo"])

    filas, aciertos = [], 0
    for caso_id, esperados in EVENTOS_ESPERADOS_AMPLIADO.items():
        obtenidos = sorted(detectados.get(caso_id, []))
        ok = obtenidos == sorted(esperados)
        aciertos += ok
        filas.append({
            "caso": caso_id,
            "estado_comercial": casos[caso_id]["estado_comercial"],
            "estado_judicial": casos[caso_id]["estado_judicial"],
            "esperado": sorted(esperados),
            "detectado": obtenidos,
            "correcto": ok,
        })
    esperados_total = sum(len(v) for v in EVENTOS_ESPERADOS_AMPLIADO.values())
    controles = [f for f in filas if not f["esperado"]]

    eventos_dos_areas = sum(
        1 for e in eventos
        if sorted(t["area"] for t in tareas if t["evento_id"] == e["id"]) == ["Comercial", "Judicial"]
    )
    criticos = [e for e in eventos if e["prioridad"] == "CRITICA"]
    criticos_coherentes = all(casos[e["caso_id"]]["estado_judicial"] in ESTADOS_JUDICIALES_APREMIO for e in criticos)
    no_disponibles = [
        {"nombre": c["nombre"], "motivo": c.get("motivo_no_disponible") or "No disponible",
         "tareas_recibidas": sum(1 for t in tareas if t["responsable_id"] == c["id"])}
        for c in repo.listar("colaboradores") if not c["disponible"]
    ]
    return {
        "casos": len(casos),
        "colaboradores": len(repo.listar("colaboradores")),
        "colaboradores_por_area": dict(Counter(c["area"] for c in repo.listar("colaboradores"))),
        "eventos_esperados": esperados_total,
        "eventos_detectados": len(eventos),
        "casos_correctos": aciertos,
        "casos_evaluados": len(filas),
        "controles_negativos": len(controles),
        "controles_negativos_sin_evento": sum(1 for f in controles if not f["detectado"]),
        "eventos_por_codigo": dict(sorted(Counter(e["codigo"] for e in eventos).items())),
        "eventos_criticos": len(criticos),
        "criticos_coherentes_con_apremio": criticos_coherentes,
        "tareas": len(tareas),
        "tareas_con_responsable": sum(1 for t in tareas if t["responsable_id"]),
        "tareas_escaladas_a_jefatura": sum(1 for t in tareas if t["asignacion"].get("escalada")),
        "eventos_con_tareas_en_ambas_areas": eventos_dos_areas,
        "colaboradores_no_disponibles": no_disponibles,
        "carga_por_colaborador": {
            nombres[cid]: n for cid, n in Counter(t["responsable_id"] for t in tareas).most_common()
        },
        "detalle": filas,
    }


# --- 2. Recorrido de la demo (caso del auto y más) -------------------------------------

def recorrido_demo(inicio: datetime) -> Dict[str, Any]:
    reloj = Reloj(inicio)
    servicio = nuevo_servicio(reloj)
    repo = servicio.repo
    nombres = _nombres(repo)
    pasos: List[Dict[str, Any]] = []

    def paso(titulo: str, lineas: List[str]):
        pasos.append({"titulo": titulo, "momento": a_iso(reloj()), "lineas": lineas})

    def describir_tarea(t: Dict[str, Any]) -> str:
        asignacion = t["asignacion"]
        responsable = nombres.get(t["responsable_id"], "sin responsable")
        puntaje = f", puntaje {asignacion['puntaje']:.2f}" if asignacion.get("puntaje") is not None else ""
        if asignacion.get("escalada"):
            puntaje = " (escalada a jefatura: ningún ejecutivo con capacidad disponible)"
        return (f"{t['id']} · {t['area']} · {t['titulo']} → **{responsable}**{puntaje}; "
                f"SLA {t['sla_horas']} h (vence {desde_iso(t['fecha_limite']).strftime('%d-%m %H:%M')})")

    # Paso 1: el comprobante del auto ya está en el repositorio al cargar el sandbox.
    evento_auto = next(e for e in repo.filtrar("eventos", caso_id="CASO-1052") if e["codigo"] == "EC-01")
    tareas_auto = repo.filtrar("tareas", evento_id=evento_auto["id"])
    comercial = next(t for t in tareas_auto if t["area"] == "Comercial")
    judicial = next(t for t in tareas_auto if t["area"] == "Judicial")
    excluidos = [f"{x['nombre']}: {x['motivo']}" for x in comercial["asignacion"].get("excluidos", [])]
    candidatos = [f"{x['nombre']} ({x['puntaje']:.2f})" for x in comercial["asignacion"].get("candidatos", [])[:4]]
    paso("1. Llega el comprobante del auto (CASO-1052, Suzuki Swift BB-CL-44)", [
        f"Evento {evento_auto['id']} {evento_auto['codigo']} detectado con prioridad **{evento_auto['prioridad']}** "
        f"y riesgo {_pesos(evento_auto['riesgo_clp'])}: la causa tiene una orden de incautación vigente.",
        "Se crean dos tareas paralelas, una por área, asignadas en el mismo instante:",
        describir_tarea(comercial),
        describir_tarea(judicial),
        "Candidatos evaluados para la tarea comercial: " + (", ".join(candidatos) or "—"),
        "Excluidos: " + ("; ".join(excluidos) or "ninguno"),
    ])

    # Paso 2: Comercial confirma el pago; el evento sigue abierto.
    reloj.avanzar(hours=1)
    r = servicio.atender_tarea(comercial["id"], "Pago confirmado", "Conciliado contra cartola.", nombres[comercial["responsable_id"]])
    paso("2. Comercial confirma el pago (1 h después)", [
        f"Tarea {comercial['id']} atendida con resultado «Pago confirmado».",
        f"El evento {evento_auto['id']} sigue **{repo.obtener('eventos', evento_auto['id'])['estado']}**. "
        f"{(r.get('motivo_cierre') or '').strip()}",
        "Cierre coordinado: confirmar el pago no basta si Judicial aún no suspende la diligencia.",
    ] + [f"Como la diligencia del auto sigue fijada, el detector crea además {e['id']} {e['codigo']} ({e['nombre']})."
         for e in r["deteccion"]["eventos_nuevos"]])

    # Paso 3: Judicial suspende dentro del plazo; el evento se cierra y el riesgo queda cubierto.
    reloj.avanzar(hours=1)
    r = servicio.atender_tarea(judicial["id"], "Diligencia suspendida preventivamente", "Escrito presentado al receptor.",
                               nombres[judicial["responsable_id"]])
    evento_cerrado = repo.obtener("eventos", evento_auto["id"])
    nuevos_auto = r["deteccion"]["eventos_nuevos"]
    metricas = servicio.estado()["metricas"]
    paso("3. Judicial suspende la diligencia (2 h después del aviso, dentro del SLA de 4 h)", [
        f"Evento {evento_cerrado['id']} **{evento_cerrado['estado']}** el {desde_iso(evento_cerrado['fecha_cierre']).strftime('%d-%m %H:%M')}.",
        f"Riesgo cubierto acumulado: {_pesos(metricas['riesgo_cubierto_clp'])} (la incautación indebida del caso real costó {_pesos(LINEA_BASE['costo_incautacion_indebida_clp'])}).",
        "Estado judicial del caso: " + repo.obtener("casos", "CASO-1052")["estado_judicial"] + ".",
    ] + [f"El detector continúa el proceso: con el pago confirmado y la causa aún viva, crea {e['id']} {e['codigo']} "
         f"({e['nombre']}) para que Judicial presente la suspensión formal." for e in nuevos_auto])

    # Paso 4: llega un comprobante por correo para el camión; se asocia por RUT.
    reloj.avanzar(minutes=30)
    camion = repo.obtener("casos", "CASO-1054")
    r = servicio.ingresar_aviso({
        "monto": 3200000, "origen": "Correo cliente", "canal": "Email",
        "datos_extraidos": {"rut_depositante": camion["deudor"]["rut"], "numero_operacion": "TRF-DEMO-0001",
                            "banco_origen": "Banco Estado"},
        "observaciones": "Comprobante adjunto en correo del deudor.",
    }, "Ingesta de comprobantes")
    aviso = r["aviso"]
    evento_camion = next(e for e in repo.filtrar("eventos", aviso_id=aviso["id"]))
    tareas_camion = repo.filtrar("tareas", evento_id=evento_camion["id"])
    desfase = (desde_iso(evento_camion["fecha_deteccion"]) - desde_iso(aviso["fecha_recepcion"])).total_seconds() / 60
    paso("4. Llega un comprobante por correo del camión KR-WP-19 (CASO-1054)", [
        f"Aviso {aviso['id']} por {_pesos(aviso['monto'])}, asociado al caso por el RUT del depositante.",
        f"Evento {evento_camion['id']} {evento_camion['codigo']} detectado en la misma operación: "
        f"**{desfase:.0f} minutos** entre la recepción y la alerta.",
    ] + [describir_tarea(t) for t in tareas_camion])

    # Paso 5: el CRM informa una orden de incautación con diligencia mañana.
    reloj.avanzar(minutes=15)
    diligencia = (reloj() + timedelta(days=1)).replace(hour=10, minute=0, second=0)
    r = servicio.actualizar_caso("CASO-1055", {
        "estado_judicial": "Orden de incautación vigente",
        "estado_comercial": "En negociación",
        "fecha_diligencia": a_iso(diligencia),
    }, "Integración CRM")
    nuevos = r["deteccion"]["eventos_nuevos"]
    lineas = ["PATCH /api/v1/casos/CASO-1055 con estado judicial «Orden de incautación vigente» y diligencia el "
              f"{diligencia.strftime('%d-%m %H:%M')}."]
    for e in nuevos:
        lineas.append(f"Evento {e['id']} {e['codigo']} ({e['nombre']}) con prioridad {e['prioridad']}.")
        lineas += [describir_tarea(t) for t in repo.filtrar("tareas", evento_id=e["id"])]
    paso("5. El CRM informa un cambio en un caso", lineas)

    # Paso 6: se programa una ausencia y sus tareas se reasignan solas.
    reloj.avanzar(minutes=15)
    pendientes = [t for t in repo.listar("tareas") if t["estado"] == "Pendiente" and t["responsable_id"]]
    carga = Counter(t["responsable_id"] for t in pendientes)
    ausente = next(cid for cid, _ in carga.most_common()
                   if repo.obtener("colaboradores", cid)["cargo"].startswith("Ejecutivo"))
    antes = {t["id"] for t in pendientes if t["responsable_id"] == ausente}
    r = servicio.registrar_ausencia(ausente, a_iso(reloj()), a_iso(reloj() + timedelta(days=2)),
                                    "Licencia médica (demo)", "RR.HH.")
    reasignadas = [repo.obtener("tareas", tid) for tid in r["reasignadas"]]
    paso(f"6. RR.HH. informa una licencia de {nombres[ausente]}", [
        f"Tenía {len(antes)} tareas pendientes; el sistema reasignó {len(reasignadas)} en el acto:",
    ] + [f"{t['id']} → {nombres.get(t['responsable_id'], 'jefatura')}" for t in reasignadas])

    # Paso 7: pasan 10 horas sin atender; las tareas vencidas se reasignan o escalan.
    reloj.avanzar(hours=10)
    r = servicio.escanear()
    escaladas = r["deteccion"]["tareas_escaladas"]
    niveles = Counter(x["nivel"] for x in escaladas)
    paso("7. Pasan 10 horas sin que nadie atienda las tareas pendientes", [
        f"{len(escaladas)} tareas vencieron: {niveles.get(1, 0)} se reasignaron a otro ejecutivo con la mitad del SLA "
        f"(nivel 1) y {niveles.get(2, 0)} pasaron a la jefatura (nivel 2). Algunos ejemplos:",
    ] + [f"{x['id']} → nivel {x['nivel']} · ahora a cargo de {nombres.get(repo.obtener('tareas', x['id'])['responsable_id'], '—')}"
         for x in escaladas[:6]] + (["El incumplimiento queda en el historial del responsable original."] if escaladas else []))

    final = servicio.estado()["metricas"]
    return {"pasos": pasos, "metricas_finales": {k: v for k, v in final.items() if k != "colaboradores"},
            "servicio": servicio}


# --- 3. Simulación de una semana de operación ------------------------------------------

PASO_SIMULACION_MIN = 15

SUPUESTOS_SIMULACION = (
    "Los avisos de pago y los cambios del CRM llegan a cualquier hora, incluso noches y fines de semana.",
    "Cada aviso se registra en el sistema al llegar (API o formulario).",
    "Cada tarea la atiende su responsable tras un tiempo tomado al azar de su propio historial para ese tipo "
    "de tarea, contado desde que la recibe; si no tiene historial (jefaturas), entre 50% y 120% del SLA. "
    "Ese historial es ficticio y no distingue tareas urgentes de normales.",
    "No se modela el horario laboral: una tarea que llega a las 3 AM se atiende igual de rápido que una de las 11 AM. "
    "En la realidad, sin un turno fuera de horario, los tiempos nocturnos y de fin de semana serían peores.",
    "Se elige el primer resultado posible de cada tarea (por ejemplo «Pago confirmado»).",
    f"La simulación avanza en pasos de {PASO_SIMULACION_MIN} min (en operación el detector corre cada minuto "
    "y después de cada cambio).",
)


def simular_operacion(inicio: datetime, dias: int = 7, avisos_por_dia: float = 8, cambios_crm: int = 12,
                      semilla: int = 2026) -> Dict[str, Any]:
    """Una semana de operación con llegadas aleatorias. Supuestos en SUPUESTOS_SIMULACION."""
    azar = random.Random(semilla)
    reloj = Reloj(inicio)
    servicio = nuevo_servicio(reloj)
    repo = servicio.repo
    fin = inicio + timedelta(days=dias)

    # Llegadas programadas.
    llegadas = []
    casos_vivos = [c["id"] for c in repo.listar("casos") if c["estado_judicial"] != "Terminado por pago"]
    for i in range(round(dias * avisos_por_dia)):
        momento = inicio + timedelta(minutes=azar.randint(10, dias * 24 * 60 - 60))
        llegadas.append((momento, "aviso", {"caso_id": azar.choice(casos_vivos),
                                            "monto": azar.randrange(80000, 2500000, 10000), "n": i}))
    candidatos_crm = [c["id"] for c in repo.listar("casos")
                      if c["estado_judicial"] in ("Notificado", "En tramitación", "Demanda presentada")]
    for i in range(min(cambios_crm, len(candidatos_crm))):
        momento = inicio + timedelta(minutes=azar.randint(10, dias * 24 * 60 - 60))
        llegadas.append((momento, "crm", {"caso_id": candidatos_crm[i],
                                          "horas_a_diligencia": azar.randint(24, 120)}))
    llegadas.sort(key=lambda x: x[0])

    agenda: Dict[str, Any] = {}       # tarea_id -> (responsable_id, momento de atención)
    avisos_sim: List[str] = []
    cambios_sim: List[Dict[str, Any]] = []

    def demora(tarea: Dict[str, Any]) -> timedelta:
        historial = [r["horas_resolucion"] for r in repo.listar("historial_desempeno")
                     if r["colaborador_id"] == tarea["responsable_id"] and r["tipo_tarea"] == tarea["tipo"]]
        horas = azar.choice(historial) if historial else tarea["sla_horas"] * azar.uniform(0.5, 1.2)
        return timedelta(hours=max(0.25, horas))

    def atender_lo_que_corresponde():
        for t in [t for t in repo.listar("tareas") if t["estado"] == "Pendiente"]:
            responsable = t["responsable_id"]
            if not responsable:
                continue
            programado = agenda.get(t["id"])
            if programado is None or programado[0] != responsable:
                # La demora corre desde que el responsable recibió la tarea, no desde el paso de la simulación.
                asignada = desde_iso(t.get("fecha_asignacion") or t["fecha_creacion"])
                agenda[t["id"]] = (responsable, asignada + demora(t))
                programado = agenda[t["id"]]
            if programado[1] <= reloj():
                resultado = next(iter(PLANTILLAS_POR_TIPO[t["tipo"]].resultados))
                servicio.atender_tarea(t["id"], resultado, "Atención simulada", responsable)

    pendientes_llegadas = list(llegadas)
    while reloj() < fin:
        # Paso de 15 min: con pasos de 1 h, el redondeo sumaba hasta 2 h a cada tarea, demasiado frente a un SLA de 4 h.
        siguiente_hora = reloj() + timedelta(minutes=PASO_SIMULACION_MIN)
        while pendientes_llegadas and pendientes_llegadas[0][0] < siguiente_hora:
            momento, tipo, datos = pendientes_llegadas.pop(0)
            reloj.ir_a(momento)
            caso = repo.obtener("casos", datos["caso_id"])
            if tipo == "aviso":
                if caso["estado_judicial"] == "Terminado por pago":
                    continue
                r = servicio.ingresar_aviso({
                    "caso_id": caso["id"], "monto": datos["monto"], "origen": "Simulación", "canal": "Email",
                    "datos_extraidos": {"rut_depositante": caso["deudor"]["rut"],
                                        "numero_operacion": f"SIM-{datos['n']:04d}"},
                }, "Ingesta de comprobantes")
                avisos_sim.append(r["aviso"]["id"])
            else:
                diligencia = reloj() + timedelta(hours=datos["horas_a_diligencia"])
                servicio.actualizar_caso(caso["id"], {
                    "estado_judicial": "Orden de incautación vigente",
                    "estado_comercial": "En negociación",
                    "fecha_diligencia": a_iso(diligencia),
                }, "Integración CRM")
                cambios_sim.append({"caso_id": caso["id"], "registrado": reloj(), "diligencia": diligencia})
        reloj.ir_a(siguiente_hora)
        servicio.escanear()
        atender_lo_que_corresponde()

    # --- Resultados ---
    eventos = repo.listar("eventos")
    tareas = repo.listar("tareas")
    avisos = {a["id"]: a for a in repo.listar("avisos")}
    eventos_sim = [e for e in eventos if desde_iso(e["fecha_deteccion"]) > inicio]
    ids_eventos_sim = {e["id"] for e in eventos_sim}
    tareas_sim = [t for t in tareas if t["evento_id"] in ids_eventos_sim]
    atendidas = [t for t in tareas_sim if t["estado"] == "Atendida"]
    a_tiempo = [t for t in atendidas if desde_iso(t["fecha_atencion"]) <= desde_iso(t["fecha_limite"])]

    alertas_aviso = []
    for aviso_id in avisos_sim:
        evento = next((e for e in eventos if e.get("aviso_id") == aviso_id and e["codigo"] == "EC-01"), None)
        if evento:
            minutos = (desde_iso(evento["fecha_deteccion"]) - desde_iso(avisos[aviso_id]["fecha_recepcion"])).total_seconds() / 60
            alertas_aviso.append(minutos)

    # Diligencias que entraron en la ventana de 72 h antes del fin de la simulación: deben quedar alertadas,
    # por EC-04 o por un evento de pago (EC-01/EC-02) del mismo caso, que tiene prioridad sobre EC-04.
    latencias_ec04, en_ventana, alertadas = [], 0, 0
    for cambio in cambios_sim:
        entra_ventana = max(cambio["registrado"], cambio["diligencia"] - timedelta(hours=72))
        if entra_ventana > fin:
            continue
        en_ventana += 1
        eventos_caso = [e for e in eventos if e["caso_id"] == cambio["caso_id"]
                        and desde_iso(e["fecha_deteccion"]) >= cambio["registrado"]]
        ec04 = next((e for e in eventos_caso if e["codigo"] == "EC-04"), None)
        cubierto_por_pago = any(e["codigo"] in ("EC-01", "EC-02") and e["estado"] == "Abierto"
                                or e["codigo"] in ("EC-01", "EC-02") and desde_iso(e["fecha_deteccion"]) <= entra_ventana
                                for e in eventos_caso)
        if ec04:
            alertadas += 1
            latencias_ec04.append((desde_iso(ec04["fecha_deteccion"]) - entra_ventana).total_seconds() / 60)
        elif cubierto_por_pago:
            alertadas += 1

    horas_atencion = [(desde_iso(t["fecha_atencion"]) - desde_iso(t["fecha_creacion"])).total_seconds() / 3600
                      for t in atendidas]
    eventos_dos_areas = sum(
        1 for e in eventos_sim
        if sorted(t["area"] for t in tareas_sim if t["evento_id"] == e["id"]) == ["Comercial", "Judicial"]
    )
    riesgo_total = sum(e["riesgo_clp"] for e in eventos_sim)
    riesgo_cubierto, criticos_cubiertos = 0, 0
    criticos = [e for e in eventos_sim if e["riesgo_clp"]]
    for e in criticos:
        judiciales = [t for t in tareas_sim if t["evento_id"] == e["id"] and t["area"] == "Judicial"]
        if judiciales and all(t in a_tiempo for t in judiciales):
            riesgo_cubierto += e["riesgo_clp"]
            criticos_cubiertos += 1
    judiciales_4h = [t for t in atendidas if t["area"] == "Judicial" and t["sla_horas"] <= 4]

    fuera_horario = sum(1 for aid in avisos_sim
                        if desde_iso(avisos[aid]["fecha_recepcion"]).weekday() >= 5
                        or not 9 <= desde_iso(avisos[aid]["fecha_recepcion"]).hour < 18)
    return {
        "dias_simulados": dias,
        "avisos_registrados": len(avisos_sim),
        "avisos_fuera_de_horario_habil": fuera_horario,
        "avisos_con_alerta_judicial": len(alertas_aviso),
        "avisos_con_alerta_judicial_pct": _pct(len(alertas_aviso), len(avisos_sim)),
        "minutos_aviso_a_alerta_max": round(max(alertas_aviso), 1) if alertas_aviso else None,
        "cambios_crm": len(cambios_sim),
        "diligencias_en_ventana_72h": en_ventana,
        "diligencias_alertadas": alertadas,
        "ec04_detectados": len(latencias_ec04),
        "minutos_ventana_72h_a_alerta_max": round(max(latencias_ec04), 1) if latencias_ec04 else None,
        "eventos_creados": len(eventos_sim),
        "eventos_por_codigo": dict(sorted(Counter(e["codigo"] for e in eventos_sim).items())),
        "eventos_cerrados": sum(1 for e in eventos_sim if e["estado"] == "Cerrado"),
        "eventos_con_tareas_en_ambas_areas_pct": _pct(eventos_dos_areas, len(eventos_sim)),
        "tareas_creadas": len(tareas_sim),
        "tareas_con_responsable_pct": _pct(sum(1 for t in tareas_sim if t["responsable_id"]), len(tareas_sim)),
        "tareas_asignadas_sin_escalar_pct": _pct(
            sum(1 for t in tareas_sim if not t["asignacion"].get("escalada") and t["nivel_escalamiento"] == 0), len(tareas_sim)),
        "tareas_reasignadas_o_escaladas_por_vencimiento": sum(1 for t in tareas_sim if t["nivel_escalamiento"] > 0),
        "tareas_atendidas": len(atendidas),
        "cumplimiento_sla_pct": _pct(len(a_tiempo), len(atendidas)),
        "horas_mediana_atencion": round(median(horas_atencion), 1) if horas_atencion else None,
        "horas_promedio_atencion": round(mean(horas_atencion), 1) if horas_atencion else None,
        "riesgo_en_juego_clp": riesgo_total,
        "riesgo_cubierto_a_tiempo_clp": riesgo_cubierto,
        "eventos_criticos": len(criticos),
        "eventos_criticos_cubiertos_a_tiempo": criticos_cubiertos,
        "tareas_judiciales_sla_4h": len(judiciales_4h),
        "tareas_judiciales_sla_4h_a_tiempo": sum(1 for t in judiciales_4h if t in a_tiempo),
        "horas_mediana_judicial_sla_4h": round(median(
            (desde_iso(t["fecha_atencion"]) - desde_iso(t["fecha_creacion"])).total_seconds() / 3600
            for t in judiciales_4h), 1) if judiciales_4h else None,
        "colaboradores_sobre_capacidad_al_final": servicio.estado()["metricas"]["tareas_sobre_capacidad"],
        "semilla": semilla,
    }


SEMILLAS_SENSIBILIDAD = tuple(range(1, 11))


def sensibilidad_simulacion(inicio: datetime, dias: int = 7, semillas=SEMILLAS_SENSIBILIDAD) -> Dict[str, Any]:
    """
    Repite la simulación con varias semillas. Las cifras de tiempos y SLA dependen del historial
    ficticio y del azar; el rango muestra cuánto varían con el mismo sistema.
    """
    filas = []
    for semilla in semillas:
        s = simular_operacion(inicio, dias=dias, semilla=semilla)
        filas.append({
            "semilla": semilla,
            "eventos_criticos": s["eventos_criticos"],
            "criticos_a_tiempo": s["eventos_criticos_cubiertos_a_tiempo"],
            "criticos_a_tiempo_pct": _pct(s["eventos_criticos_cubiertos_a_tiempo"], s["eventos_criticos"]),
            "cumplimiento_sla_pct": s["cumplimiento_sla_pct"],
            "horas_mediana_judicial_sla_4h": s["horas_mediana_judicial_sla_4h"],
        })

    def rango(clave: str) -> Dict[str, Optional[float]]:
        valores = [f[clave] for f in filas if f[clave] is not None]
        if not valores:
            return {"min": None, "mediana": None, "max": None}
        return {"min": min(valores), "mediana": round(median(valores), 1), "max": max(valores)}

    return {
        "semillas": list(semillas),
        "filas": filas,
        "criticos_a_tiempo_pct": rango("criticos_a_tiempo_pct"),
        "cumplimiento_sla_pct": rango("cumplimiento_sla_pct"),
        "horas_mediana_judicial_sla_4h": rango("horas_mediana_judicial_sla_4h"),
    }


# --- 4. Pruebas unitarias -------------------------------------------------------------

def correr_pruebas() -> Dict[str, Any]:
    salida = io.StringIO()
    suite = unittest.TestLoader().discover(
        start_dir=os.path.join(DIRECTORIO_MOTOR, "tests"), top_level_dir=DIRECTORIO_MOTOR)
    resultado = unittest.TextTestRunner(stream=salida, verbosity=2).run(suite)
    return {
        "ejecutadas": resultado.testsRun,
        "fallidas": len(resultado.failures),
        "errores": len(resultado.errors),
        "omitidas": len(resultado.skipped),
        "ok": resultado.wasSuccessful(),
        "salida": salida.getvalue(),
    }


# --- Redacción de los archivos ----------------------------------------------------------

def _md_deteccion(d: Dict[str, Any]) -> str:
    l = [
        "# Detección con el escenario ampliado",
        "",
        f"Sandbox con **{d['casos']} casos** y **{d['colaboradores']} colaboradores** "
        f"({', '.join(f'{n} {a}' for a, n in d['colaboradores_por_area'].items())}), todos ficticios.",
        "",
        f"- Casos con el resultado esperado: **{d['casos_correctos']} de {d['casos_evaluados']}**.",
        f"- Eventos esperados: {d['eventos_esperados']} · detectados: {d['eventos_detectados']}.",
        f"- Controles negativos (casos que NO deben generar eventos): {d['controles_negativos_sin_evento']} de {d['controles_negativos']} sin evento.",
        f"- Eventos por código: {', '.join(f'{k}: {v}' for k, v in d['eventos_por_codigo'].items())}.",
        f"- Eventos críticos: {d['eventos_criticos']} (todos en causas con apremio: {'sí' if d['criticos_coherentes_con_apremio'] else 'NO'}).",
        f"- Tareas: {d['tareas']} · con responsable: {d['tareas_con_responsable']} · escaladas a jefatura: {d['tareas_escaladas_a_jefatura']}.",
        f"- Eventos con una tarea en cada área: {d['eventos_con_tareas_en_ambas_areas']} de {d['eventos_detectados']}.",
        "",
        "## Colaboradores no disponibles al cargar",
        "",
    ]
    for c in d["colaboradores_no_disponibles"]:
        l.append(f"- {c['nombre']}: {c['motivo']} → recibió {c['tareas_recibidas']} tareas.")
    l += ["", "## Caso por caso", "", "| Caso | Estado comercial | Estado judicial | Esperado | Detectado | OK |",
          "|---|---|---|---|---|---|"]
    for f in d["detalle"]:
        l.append(f"| {f['caso']} | {f['estado_comercial']} | {f['estado_judicial']} | "
                 f"{', '.join(f['esperado']) or '—'} | {', '.join(f['detectado']) or '—'} | {'✔' if f['correcto'] else '✘'} |")
    return "\n".join(l) + "\n"


def _md_recorrido(r: Dict[str, Any]) -> str:
    l = ["# Recorrido de la demo", "",
         "Ejecutado automáticamente sobre el sandbox ampliado (datos ficticios). Cada paso usa los mismos casos de uso "
         "que la API REST y la interfaz.", ""]
    for p in r["pasos"]:
        l += [f"## {p['titulo']}", "", f"_{p['momento']}_", ""]
        l += [f"- {x}" for x in p["lineas"]]
        l.append("")
    m = r["metricas_finales"]
    l += ["## Métricas del dashboard al final del recorrido", "",
          f"- Eventos abiertos: {m['eventos_abiertos']} (críticos: {m['eventos_criticos_abiertos']}) · cerrados: {m['eventos_cerrados']}",
          f"- Tareas pendientes: {m['tareas_pendientes']} · atendidas: {m['tareas_atendidas']} · vencidas: {m['tareas_vencidas']}",
          f"- Minutos promedio aviso → alerta: {m['minutos_promedio_aviso_a_alerta']}",
          f"- Riesgo expuesto: {_pesos(m['riesgo_expuesto_clp'])} · cubierto: {_pesos(m['riesgo_cubierto_clp'])}",
          f"- Tareas reasignadas o escaladas por vencimiento: {m['tareas_escaladas_por_vencimiento']}", ""]
    return "\n".join(l)


def _md_simulacion(s: Dict[str, Any], sens: Dict[str, Any]) -> str:
    supuestos = SUPUESTOS_SIMULACION
    return "\n".join([
        f"# Simulación de {s['dias_simulados']} días de operación",
        "",
        "**Simulación con datos ficticios.** Sirve para estimar el comportamiento del sistema, no reemplaza la medición "
        "con datos reales de Cobgestion en el piloto.",
        "",
        "## Supuestos",
        "",
        *[f"- {x}" for x in supuestos],
        f"- Semilla aleatoria: {s['semilla']} (con la misma semilla y hora de inicio, el resultado se repite; las cifras varían levemente según la hora en que se genera).",
        "",
        "## Resultados",
        "",
        "| Indicador | Resultado simulado | Situación actual (diagnóstico) |",
        "|---|---|---|",
        f"| Avisos de pago registrados | {s['avisos_registrados']} ({s['avisos_fuera_de_horario_habil']} fuera de horario hábil) | — |",
        f"| Avisos que generan alerta a Judicial | {_n(s['avisos_con_alerta_judicial_pct'])}% | Depende de que alguien avise por WhatsApp |",
        f"| Tiempo máximo aviso → alerta | {_n(s['minutos_aviso_a_alerta_max'])} min | Mediana {_n(LINEA_BASE['mediana_horas_deteccion_conflictos'])} h; 10% más lento > {LINEA_BASE['p90_horas_deteccion_conflictos']} h |",
        f"| Diligencias que entraron en la ventana de 72 h | {s['diligencias_alertadas']} de {s['diligencias_en_ventana_72h']} alertadas (EC-04, o EC-01/EC-02 si había un pago pendiente); demora máx. {_n(s['minutos_ventana_72h_a_alerta_max'])} min por el escaneo horario de la simulación | Sin alerta sistemática |",
        f"| Eventos con tareas en ambas áreas | {_n(s['eventos_con_tareas_en_ambas_areas_pct'])}% | — |",
        f"| Tareas con responsable asignado | {_n(s['tareas_con_responsable_pct'])}% | No siempre está claro quién actúa |",
        f"| Tareas asignadas sin escalar | {_n(s['tareas_asignadas_sin_escalar_pct'])}% | — |",
        f"| Tareas reasignadas o escaladas por vencimiento | {s['tareas_reasignadas_o_escaladas_por_vencimiento']} | — |",
        f"| Cumplimiento de SLA | {_n(s['cumplimiento_sla_pct'])}% de {s['tareas_atendidas']} tareas atendidas | — |",
        f"| Horas de atención (mediana / promedio) | {_n(s['horas_mediana_atencion'])} / {_n(s['horas_promedio_atencion'])} h | — |",
        f"| Eventos críticos con la tarea judicial dentro de su SLA crítico | {s['eventos_criticos_cubiertos_a_tiempo']} de {s['eventos_criticos']} ({_pesos(s['riesgo_cubierto_a_tiempo_clp'])} de {_pesos(s['riesgo_en_juego_clp'])} en costas) | Caso real: {_pesos(LINEA_BASE['costo_incautacion_indebida_clp'])} perdidos |",
        f"| Eventos creados / cerrados | {s['eventos_creados']} / {s['eventos_cerrados']} | — |",
        "",
        "El cumplimiento de SLA y el tiempo de atención dependen del historial ficticio de cada colaborador; "
        "con datos reales del piloto estos valores deben recalcularse.",
        "",
        "## Sensibilidad: la misma simulación con otras semillas",
        "",
        f"Se repitió la semana con {len(sens['semillas'])} semillas aleatorias distintas, sin cambiar el sistema:",
        "",
        "| Indicador | Mínimo | Mediana | Máximo |",
        "|---|---|---|---|",
        f"| Eventos críticos con la tarea judicial a tiempo (%) | {_n(sens['criticos_a_tiempo_pct']['min'])} | "
        f"{_n(sens['criticos_a_tiempo_pct']['mediana'])} | {_n(sens['criticos_a_tiempo_pct']['max'])} |",
        f"| Cumplimiento de SLA (%) | {_n(sens['cumplimiento_sla_pct']['min'])} | {_n(sens['cumplimiento_sla_pct']['mediana'])} | "
        f"{_n(sens['cumplimiento_sla_pct']['max'])} |",
        f"| Mediana de atención de tareas judiciales con SLA de 4 h (h) | {_n(sens['horas_mediana_judicial_sla_4h']['min'])} | "
        f"{_n(sens['horas_mediana_judicial_sla_4h']['mediana'])} | {_n(sens['horas_mediana_judicial_sla_4h']['max'])} |",
        "",
        "**Cómo leer estas cifras.** La amplitud del rango muestra que el cumplimiento del SLA crítico depende del azar y "
        "de los tiempos de respuesta ficticios del sandbox, no de una característica de Cobgestion: **no es un hallazgo "
        "para presentar como resultado**. Lo que sí demuestra la simulación es que el sistema alerta de inmediato, mide "
        "el cumplimiento de cada plazo y reasigna o escala lo que vence. El valor real del cumplimiento debe medirse en un "
        "piloto con datos de Cobgestion, donde además conviene validar si el SLA de 4 h es adecuado y quién responde "
        "fuera del horario laboral (la simulación no modela turnos).",
        "",
    ])


CHECKLIST = """# Capturas de la interfaz para la presentación

Levanta la aplicación con `npm run dev`, presiona **Reiniciar sandbox** y saca estas capturas en orden.
Así coinciden con recorrido_demo.md.

1. **Repositorio**: lista de casos (24) y ficha de CASO-1052 con su historial de cambios.
2. **Detector**: eventos detectados al cargar, con EC-01 del CASO-1052 en prioridad crítica y SLA judicial de 4 h.
3. **Asignación**: panel «¿Por qué esta persona?» de la tarea comercial del CASO-1052 (Camila excluida por su permiso).
4. **Asignación**: un colaborador con licencia o capacitación (Felipe Ortega, Tomás Navarro) y cómo el sistema lo excluye.
5. **Cierre coordinado**: marca como atendida la tarea comercial («Pago confirmado») y muestra que el evento sigue abierto.
6. **Registrar comprobante**: registra el correo del camión KR-WP-19 y muestra el evento creado en el acto.
7. **Dashboard**: métricas, carga por colaborador, riesgo expuesto y cubierto, auditoría.
8. **Terminal**: `npm test` con todas las pruebas en OK, y `npm run evidencia` terminado.

No uses la extracción con Gemini para las capturas salvo que sea necesario: el plan gratuito permite 20 solicitudes al día.
"""


def _md_resumen(fecha: str, d: Dict[str, Any], r: Dict[str, Any], s: Dict[str, Any], sens: Dict[str, Any],
                p: Optional[Dict[str, Any]]) -> str:
    pasos = r["pasos"]
    l = [
        "# Evidencia del prototipo · Sistema Integrado de Eventos Críticos",
        "",
        f"Generado el {fecha} con `npm run evidencia`. Datos ficticios del sandbox; no incluye datos reales de Cobgestion.",
        "",
        "## Cifras para la presentación",
        "",
    ]
    if p:
        l.append(f"- **Pruebas automatizadas:** {p['ejecutadas']} ejecutadas, "
                 f"{p['ejecutadas'] - p['fallidas'] - p['errores']} OK"
                 + (f", {p['fallidas']} fallidas y {p['errores']} con error" if not p["ok"] else "") + ".")
    l += [
        f"- **Sandbox:** {d['casos']} casos y {d['colaboradores']} colaboradores.",
        f"- **Detección:** {d['casos_correctos']} de {d['casos_evaluados']} casos con el resultado esperado; "
        f"{d['eventos_detectados']} eventos de los 5 tipos del catálogo; {d['controles_negativos_sin_evento']} de "
        f"{d['controles_negativos']} controles negativos sin falsas alertas.",
        f"- **Asignación:** {d['tareas_con_responsable']} de {d['tareas']} tareas con responsable automático; "
        f"{d['eventos_con_tareas_en_ambas_areas']} de {d['eventos_detectados']} eventos con una tarea en cada área; "
        "nadie con licencia o permiso recibe tareas.",
        f"- **Simulación de {s['dias_simulados']} días:** {s['avisos_registrados']} avisos "
        f"({s['avisos_fuera_de_horario_habil']} fuera de horario hábil); {_n(s['avisos_con_alerta_judicial_pct'])}% con alerta a Judicial "
        f"en máximo {_n(s['minutos_aviso_a_alerta_max'])} min desde su registro, frente a la mediana actual de "
        f"{_n(LINEA_BASE['mediana_horas_deteccion_conflictos'])} h; {_n(s['tareas_con_responsable_pct'])}% de las tareas con responsable; "
        f"cumplimiento de SLA {_n(s['cumplimiento_sla_pct'])}% en la corrida principal (entre "
        f"{_n(sens['cumplimiento_sla_pct']['min'])}% y {_n(sens['cumplimiento_sla_pct']['max'])}% en "
        f"{len(sens['semillas'])} corridas). Las cifras de cumplimiento dependen de tiempos ficticios: ver simulacion.md.",
        "",
        "## Recorrido de la demo",
        "",
    ]
    l += [f"- {x['titulo']}" for x in pasos]
    l += [
        "",
        "## Archivos",
        "",
        "| Archivo | Contenido |",
        "|---|---|",
        "| deteccion.md | Eventos esperados frente a detectados, caso por caso |",
        "| recorrido_demo.md | El caso del auto y los demás pasos de la demo, con responsables y plazos |",
        "| simulacion.md | Supuestos y resultados de la semana simulada |",
        "| metricas.json | Todas las cifras en formato máquina |",
        "| pruebas.txt | Salida completa de las pruebas unitarias |",
        "| exportaciones/ | Hojas del repositorio al final del recorrido, en CSV para Excel |",
        "| checklist_capturas.md | Capturas de la interfaz que conviene sacar a mano |",
        "",
        "## Qué no demuestra este paquete",
        "",
        "- No hay datos reales de Cobgestion ni conexión al CRM real: la integración está lista (API REST e importador de casos) pero falta el acceso.",
        "- El catálogo de eventos, la matriz RACI y los SLA están pendientes de validación con Cobgestion.",
        "- Los tiempos de atención de la simulación salen del historial ficticio del sandbox, y la simulación no modela "
        "el horario laboral: el cumplimiento de SLA simulado no es una estimación del real.",
        "- El tiempo aviso → alerta se mide desde que el comprobante se **registra**. Los avisos automáticos del banco "
        "pueden entrar por API, pero un pantallazo de WhatsApp todavía requiere que alguien lo ingrese.",
        "",
    ]
    return "\n".join(l)


def generar(directorio: Optional[str] = None, incluir_pruebas: bool = True, dias_simulacion: int = 7,
            inicio: Optional[datetime] = None, semillas_sensibilidad=SEMILLAS_SENSIBILIDAD) -> Dict[str, Any]:
    inicio = (inicio or datetime.now()).replace(microsecond=0)
    fecha = inicio.strftime("%Y-%m-%d_%H%M")
    directorio = directorio or os.path.join(DIRECTORIO_RAIZ, "evidencia", fecha)
    os.makedirs(directorio, exist_ok=True)

    deteccion = verificar_deteccion(inicio)
    recorrido = recorrido_demo(inicio)
    simulacion = simular_operacion(inicio, dias=dias_simulacion)
    sensibilidad = sensibilidad_simulacion(inicio, dias=dias_simulacion, semillas=semillas_sensibilidad)
    pruebas = correr_pruebas() if incluir_pruebas else None

    archivos = {
        "README.md": _md_resumen(inicio.strftime("%d-%m-%Y %H:%M"), deteccion, recorrido, simulacion, sensibilidad, pruebas),
        "deteccion.md": _md_deteccion(deteccion),
        "recorrido_demo.md": _md_recorrido(recorrido),
        "simulacion.md": _md_simulacion(simulacion, sensibilidad),
        "checklist_capturas.md": CHECKLIST,
        "metricas.json": json.dumps({
            "generado": a_iso(inicio),
            "linea_base_diagnostico": LINEA_BASE,
            "deteccion": {k: v for k, v in deteccion.items() if k != "detalle"},
            "recorrido": recorrido["metricas_finales"],
            "simulacion": simulacion,
            "sensibilidad_simulacion": sensibilidad,
            "pruebas": {k: v for k, v in pruebas.items() if k != "salida"} if pruebas else None,
        }, ensure_ascii=False, indent=2),
    }
    if pruebas:
        archivos["pruebas.txt"] = pruebas["salida"]
    for nombre, contenido in archivos.items():
        with open(os.path.join(directorio, nombre), "w", encoding="utf-8") as f:
            f.write(contenido)
    recorrido["servicio"].exportar(os.path.join(directorio, "exportaciones"))
    return {"directorio": directorio, "deteccion": deteccion, "simulacion": simulacion,
            "sensibilidad": sensibilidad, "pruebas": pruebas}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Genera el paquete de evidencia del prototipo.")
    parser.add_argument("--sin-pruebas", action="store_true", help="No ejecutar las pruebas unitarias")
    parser.add_argument("--dias", type=int, default=7, help="Días a simular (por defecto 7)")
    parser.add_argument("--salida", help="Carpeta de salida (por defecto evidencia/<fecha_hora>)")
    args = parser.parse_args()

    r = generar(args.salida, incluir_pruebas=not args.sin_pruebas, dias_simulacion=args.dias)
    d, s, p = r["deteccion"], r["simulacion"], r["pruebas"]
    print(f"Evidencia generada en: {r['directorio']}")
    if p:
        print(f"  Pruebas: {p['ejecutadas']} ejecutadas, {'todas OK' if p['ok'] else 'CON FALLAS'}")
    print(f"  Detección: {d['casos_correctos']}/{d['casos_evaluados']} casos correctos, {d['eventos_detectados']} eventos")
    print(f"  Asignación: {d['tareas_con_responsable']}/{d['tareas']} tareas con responsable")
    print(f"  Simulación {s['dias_simulados']} días: {s['avisos_registrados']} avisos, alerta máx. "
          f"{s['minutos_aviso_a_alerta_max']} min, SLA {s['cumplimiento_sla_pct']}%")
    return 0 if (p is None or p["ok"]) else 1


if __name__ == "__main__":
    sys.exit(main())
