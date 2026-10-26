"""
Módulo de asignación de tareas: matriz RACI + modelo de asignación óptima.

1. La matriz RACI define, por tipo de tarea, qué cargo es Responsable (R) de
   ejecutarla, quién Aprueba/rinde cuentas (A), a quién se Consulta (C) y a quién
   se Informa (I).

2. Entre los colaboradores con el cargo R se elige al más adecuado resolviendo un
   problema de asignación (investigación de operaciones):

       max  Σ puntaje(c, t) · x(c, t)
       s.a. cada tarea t se asigna a exactamente un colaborador
            Σ_t x(c, t) ≤ capacidad libre de c
            x(c, t) = 0 si c no está disponible, no tiene la competencia o no tiene el cargo R
            x(c, t) = 0 si c tiene una ausencia programada antes del vencimiento de t

   El puntaje combina el historial del colaborador y su disponibilidad:

       puntaje = w_exp · experiencia + w_des · desempeño + w_disp · disponibilidad + w_cont · continuidad

       experiencia    = n / (n + 5), con n = tareas de ese tipo atendidas antes
       desempeño      = (cumplidas en SLA + 1) / (n + 2)   (suavizado de Laplace)
       disponibilidad = 1 − carga / capacidad              (la carga sube con cada tarea del lote)
       continuidad    = 1 si es el titular del caso en su área

   Se resuelve con el método húngaro sobre una matriz tareas × "cupos" (cada
   colaborador aporta tantos cupos como capacidad libre). Si una tarea no tiene
   ningún colaborador factible, se escala al cargo A (jefatura del área).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from modelo.entidades import a_iso, desde_iso
from modelo.repositorio import Repositorio

MATRIZ_RACI: Dict[str, Dict[str, str]] = {
    "VERIFICAR_PAGO":                {"Ejecutivo Comercial": "R", "Jefe Comercial": "A", "Ejecutivo Judicial": "I", "Jefe Judicial": "-"},
    "ACLARAR_DISCREPANCIA":          {"Ejecutivo Comercial": "R", "Jefe Comercial": "A", "Ejecutivo Judicial": "I", "Jefe Judicial": "-"},
    "REGISTRAR_PAGO_CRM":            {"Ejecutivo Comercial": "R", "Jefe Comercial": "A", "Ejecutivo Judicial": "-", "Jefe Judicial": "-"},
    "CONTACTAR_DEUDOR":              {"Ejecutivo Comercial": "R", "Jefe Comercial": "A", "Ejecutivo Judicial": "C", "Jefe Judicial": "-"},
    "GESTIONAR_REPACTACION":         {"Ejecutivo Comercial": "R", "Jefe Comercial": "A", "Ejecutivo Judicial": "C", "Jefe Judicial": "I"},
    "EVALUAR_SUSPENSION":            {"Ejecutivo Comercial": "C", "Jefe Comercial": "I", "Ejecutivo Judicial": "R", "Jefe Judicial": "A"},
    "EVALUAR_CURSO_CAUSA":           {"Ejecutivo Comercial": "C", "Jefe Comercial": "-", "Ejecutivo Judicial": "R", "Jefe Judicial": "A"},
    "FORMALIZAR_SUSPENSION_TERMINO": {"Ejecutivo Comercial": "I", "Jefe Comercial": "I", "Ejecutivo Judicial": "R", "Jefe Judicial": "A"},
    "CONFIRMAR_DILIGENCIA":          {"Ejecutivo Comercial": "C", "Jefe Comercial": "-", "Ejecutivo Judicial": "R", "Jefe Judicial": "A"},
    "REACTIVAR_CAUSA":               {"Ejecutivo Comercial": "C", "Jefe Comercial": "I", "Ejecutivo Judicial": "R", "Jefe Judicial": "A"},
}

PESOS = {
    "normal":  {"experiencia": 0.30, "desempeno": 0.25, "disponibilidad": 0.30, "continuidad": 0.15},
    # En una tarea crítica importa más que alguien la tome ya y la cumpla a tiempo
    # (el caso del auto: el titular no estaba y nadie más tomó el comprobante).
    "CRITICA": {"experiencia": 0.20, "desempeno": 0.30, "disponibilidad": 0.40, "continuidad": 0.10},
}

COSTO_INFACTIBLE = 1e6
COSTO_ESCALAMIENTO = 10.0


# --- Historial y carga ------------------------------------------------------------

def perfil_historico(repo: Repositorio, colaborador_id: str, tipo_tarea: Optional[str] = None) -> Dict[str, Any]:
    registros = [
        r for r in repo.listar("historial_desempeno")
        if r["colaborador_id"] == colaborador_id and (tipo_tarea is None or r["tipo_tarea"] == tipo_tarea)
    ]
    n = len(registros)
    cumplidas = sum(1 for r in registros if r["cumplio_sla"])
    return {
        "tareas": n,
        "cumplidas_sla": cumplidas,
        "tasa_sla": round(cumplidas / n, 3) if n else None,
        "horas_promedio": round(sum(r["horas_resolucion"] for r in registros) / n, 1) if n else None,
    }


def carga_actual(repo: Repositorio, colaborador: Dict[str, Any]) -> int:
    pendientes = sum(
        1 for t in repo.listar("tareas")
        if t["estado"] == "Pendiente" and t["responsable_id"] == colaborador["id"]
    )
    return colaborador.get("tareas_externas", 0) + pendientes


def _cargo_responsable(tipo_tarea: str) -> str:
    return next(cargo for cargo, letra in MATRIZ_RACI[tipo_tarea].items() if letra == "R")


def _es_titular(colaborador: Dict[str, Any], caso: Dict[str, Any]) -> bool:
    campo = "responsable_comercial" if colaborador["area"] == "Comercial" else "responsable_judicial"
    return caso.get(campo) == colaborador["id"]


def ausencia_en_ventana(colaborador: Dict[str, Any], inicio: datetime, fin: datetime) -> Optional[Dict[str, str]]:
    """Primera ausencia programada que se cruza con el intervalo [inicio, fin)."""
    return next(
        (
            a for a in colaborador.get("ausencias", [])
            if desde_iso(a["desde"]) < fin and desde_iso(a["hasta"]) > inicio
        ),
        None,
    )


def fin_ventana(tarea: Dict[str, Any], ahora: datetime) -> datetime:
    """Hasta cuándo debe estar disponible quien tome la tarea (su plazo vigente)."""
    plazos = [desde_iso(tarea["fecha_limite"])]
    if tarea.get("plazo_escalamiento"):
        plazos.append(desde_iso(tarea["plazo_escalamiento"]))
    return max(plazos + [ahora])


def motivo_exclusion(colaborador: Dict[str, Any], tarea: Dict[str, Any], carga: int, ahora: datetime) -> Optional[str]:
    if colaborador["cargo"] != _cargo_responsable(tarea["tipo"]):
        return "cargo distinto al Responsable (R) de la matriz RACI"
    if not colaborador["disponible"]:
        return f"no disponible ({colaborador.get('motivo_no_disponible') or 'sin motivo informado'})"
    ausencia = ausencia_en_ventana(colaborador, ahora, fin_ventana(tarea, ahora))
    if ausencia:
        inicio = desde_iso(ausencia["desde"]).strftime("%d-%m %H:%M")
        return f"ausencia programada desde el {inicio} ({ausencia['motivo']}), antes del vencimiento"
    if tarea["tipo"] not in colaborador["competencias"]:
        return "sin competencia registrada para este tipo de tarea"
    if carga >= colaborador["capacidad_max"]:
        return f"sin capacidad libre ({carga}/{colaborador['capacidad_max']})"
    return None


def puntaje(
    repo: Repositorio,
    colaborador: Dict[str, Any],
    tarea: Dict[str, Any],
    caso: Dict[str, Any],
    carga: int,
) -> Tuple[float, Dict[str, float]]:
    perfil = perfil_historico(repo, colaborador["id"], tarea["tipo"])
    n = perfil["tareas"]
    criterios = {
        "experiencia": n / (n + 5),
        "desempeno": (perfil["cumplidas_sla"] + 1) / (n + 2),
        "disponibilidad": max(0.0, 1 - carga / colaborador["capacidad_max"]),
        "continuidad": 1.0 if _es_titular(colaborador, caso) else 0.0,
    }
    pesos = PESOS["CRITICA"] if tarea["prioridad"] == "CRITICA" else PESOS["normal"]
    total = sum(pesos[k] * v for k, v in criterios.items())
    return round(total, 4), {k: round(v, 3) for k, v in criterios.items()}


# --- Método húngaro -------------------------------------------------------------------

def metodo_hungaro(costos: Sequence[Sequence[float]]) -> List[int]:
    """
    Asignación de costo mínimo para una matriz n × m con n ≤ m (Kuhn-Munkres, O(n²m)).
    Devuelve, para cada fila, el índice de la columna asignada.
    """
    n = len(costos)
    if n == 0:
        return []
    m = len(costos[0])
    if n > m:
        raise ValueError("El método húngaro requiere al menos tantas columnas como filas")

    u = [0.0] * (n + 1)
    v = [0.0] * (m + 1)
    p = [0] * (m + 1)       # p[j] = fila asignada a la columna j (1-indexado, 0 = libre)
    camino = [0] * (m + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minimo = [float("inf")] * (m + 1)
        usado = [False] * (m + 1)
        while True:
            usado[j0] = True
            i0 = p[j0]
            delta = float("inf")
            j1 = 0
            for j in range(1, m + 1):
                if usado[j]:
                    continue
                reducido = costos[i0 - 1][j - 1] - u[i0] - v[j]
                if reducido < minimo[j]:
                    minimo[j] = reducido
                    camino[j] = j0
                if minimo[j] < delta:
                    delta = minimo[j]
                    j1 = j
            for j in range(m + 1):
                if usado[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minimo[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = camino[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    asignacion = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            asignacion[p[j] - 1] = j - 1
    return asignacion


# --- Asignación de un lote de tareas ------------------------------------------------

def asignar_lote(
    repo: Repositorio,
    tareas: List[Dict[str, Any]],
    ahora: datetime,
    usuario: str = "Asignador automático",
    excluir: Optional[Dict[str, str]] = None,
) -> None:
    """
    Asigna responsable y RACI a cada tarea del lote resolviendo el problema de asignación.
    `excluir` mapea tarea_id -> colaborador_id que no puede recibirla (reasignaciones).
    """
    if not tareas:
        return
    excluir = {k: v for k, v in (excluir or {}).items() if v}
    colaboradores = repo.listar("colaboradores")
    casos = {t["caso_id"]: repo.obtener("casos", t["caso_id"]) for t in tareas}
    ids_lote = {t["id"] for t in tareas}

    # Carga sin contar las tareas del lote (pueden estar siendo reasignadas).
    cargas = {
        c["id"]: c.get("tareas_externas", 0) + sum(
            1 for t in repo.listar("tareas")
            if t["estado"] == "Pendiente" and t["responsable_id"] == c["id"] and t["id"] not in ids_lote
        )
        for c in colaboradores
    }

    # Columnas: un cupo por cada unidad de capacidad libre de cada colaborador.
    cupos: List[Tuple[Dict[str, Any], int]] = []
    for c in colaboradores:
        for k in range(max(0, c["capacidad_max"] - cargas[c["id"]])):
            cupos.append((c, k))

    costos = []
    for t in tareas:
        fila = []
        for c, k in cupos:
            carga = cargas[c["id"]] + k
            if excluir.get(t["id"]) == c["id"] or motivo_exclusion(c, t, carga, ahora):
                fila.append(COSTO_INFACTIBLE)
            else:
                fila.append(1 - puntaje(repo, c, t, casos[t["caso_id"]], carga)[0])
        # Columna ficticia propia de la tarea: escalar a la jefatura si no hay nadie factible.
        fila.extend(COSTO_ESCALAMIENTO if j == len(costos) else COSTO_INFACTIBLE for j in range(len(tareas)))
        costos.append(fila)

    solucion = metodo_hungaro(costos)
    metodo = f"Método húngaro (lote de {len(tareas)} tarea{'s' if len(tareas) != 1 else ''})"

    for i, t in enumerate(tareas):
        caso = casos[t["caso_id"]]
        evaluacion = _evaluar_candidatos(repo, t, caso, cargas, excluir.get(t["id"]), ahora)
        columna = solucion[i]
        t["fecha_asignacion"] = a_iso(ahora)
        if columna < len(cupos) and costos[i][columna] < COSTO_INFACTIBLE:
            elegido, k = cupos[columna]
            total, criterios = puntaje(repo, elegido, t, caso, cargas[elegido["id"]] + k)
            t["responsable_id"] = elegido["id"]
            t["asignacion"] = {
                "metodo": metodo,
                "escalada": False,
                "puntaje": total,
                "criterios": criterios,
                "pesos": PESOS["CRITICA"] if t["prioridad"] == "CRITICA" else PESOS["normal"],
                **evaluacion,
            }
            detalle = f"{t['titulo']} → {elegido['nombre']} (puntaje {total:.2f})."
        else:
            jefe = asignar_a_jefatura(repo, t, "Escalada a jefatura: ningún colaborador factible", evaluacion)
            detalle = f"{t['titulo']} → escalada a {jefe['nombre'] if jefe else 'jefatura'} (sin colaborador factible)."

        repo.registrar_historial(
            usuario=usuario,
            area="Sistema",
            accion="Tarea asignada",
            detalle=detalle,
            entidad="Tarea",
            entidad_id=t["id"],
            caso_id=t["caso_id"],
            ahora=ahora,
        )

    # La RACI se resuelve al final: C/I del otro área apuntan al responsable de la tarea hermana.
    for t in tareas:
        t["raci"] = resolver_raci(repo, t, casos[t["caso_id"]])


def _evaluar_candidatos(
    repo: Repositorio,
    tarea: Dict[str, Any],
    caso: Dict[str, Any],
    cargas: Dict[str, int],
    excluido_id: Optional[str],
    ahora: datetime,
) -> Dict[str, Any]:
    """Ranking de candidatos y motivos de exclusión, para explicar la decisión en la interfaz."""
    candidatos, excluidos = [], []
    cargo_r = _cargo_responsable(tarea["tipo"])
    for c in repo.listar("colaboradores"):
        if c["cargo"] != cargo_r:
            continue
        carga = cargas[c["id"]]
        motivo = "responsable anterior de la tarea" if c["id"] == excluido_id else motivo_exclusion(c, tarea, carga, ahora)
        if motivo:
            excluidos.append({"id": c["id"], "nombre": c["nombre"], "motivo": motivo})
        else:
            total, criterios = puntaje(repo, c, tarea, caso, carga)
            candidatos.append({"id": c["id"], "nombre": c["nombre"], "puntaje": total, "criterios": criterios})
    candidatos.sort(key=lambda x: x["puntaje"], reverse=True)
    return {"candidatos": candidatos, "excluidos": excluidos}


def asignar_a_jefatura(
    repo: Repositorio,
    tarea: Dict[str, Any],
    metodo: str,
    evaluacion: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Deja la tarea en manos del cargo A de la matriz RACI (la jefatura del área)."""
    cargo_a = next((cargo for cargo, letra in MATRIZ_RACI[tarea["tipo"]].items() if letra == "A"), None)
    jefe = next((c for c in repo.listar("colaboradores") if c["cargo"] == cargo_a), None)
    tarea["responsable_id"] = jefe["id"] if jefe else None
    tarea["asignacion"] = {
        "metodo": metodo,
        "escalada": True,
        "puntaje": None,
        "criterios": {},
        "pesos": {},
        "candidatos": [],
        "excluidos": [],
        **(evaluacion or {}),
    }
    return jefe


def resolver_raci(repo: Repositorio, tarea: Dict[str, Any], caso: Dict[str, Any]) -> Dict[str, List[str]]:
    raci: Dict[str, List[str]] = {"R": [], "A": [], "C": [], "I": []}
    if tarea.get("responsable_id"):
        raci["R"].append(tarea["responsable_id"])
    hermanas = [
        h for h in repo.filtrar("tareas", evento_id=tarea["evento_id"])
        if h["id"] != tarea["id"] and h.get("responsable_id")
    ]
    for cargo, letra in MATRIZ_RACI[tarea["tipo"]].items():
        if letra not in ("A", "C", "I"):
            continue
        if cargo.startswith("Jefe"):
            personas = [c["id"] for c in repo.filtrar("colaboradores", cargo=cargo)]
        else:
            area = cargo.split()[-1]
            personas = [h["responsable_id"] for h in hermanas if h["area"] == area]
            if not personas:
                titular = caso["responsable_comercial"] if area == "Comercial" else caso["responsable_judicial"]
                personas = [titular]
        for p in personas:
            if p not in raci[letra] and p not in raci["R"]:
                raci[letra].append(p)
    return raci
