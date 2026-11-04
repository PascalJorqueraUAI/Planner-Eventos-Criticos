"""
Permisos por nivel de cargo y vista de los datos según quién consulta.

  Nivel 1 · Gerente General y Subgerente: acceso completo.
  Nivel 2 · Gerente Comercial y Gerente Judicial: todo lo de su área (tareas, equipo,
            campos del caso) y la operación general (crear e importar casos).
  Nivel 3 · Ejecutivos y abogados: ven todos los casos para coordinarse, pero en los que
            no llevan se ocultan los datos personales del deudor (Ley 21.719: acceso
            limitado a lo necesario). Actúan sobre sus propias tareas y casos.

Las reglas se validan aquí, en el motor, para cada comando: la interfaz solo oculta
botones según los permisos que este módulo le informa.
"""

import copy
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from modelo.repositorio import Repositorio
from modelo.usuarios import publico


class PermisoDenegado(Exception):
    pass


@dataclass(frozen=True)
class Actor:
    id: str
    nombre: str
    nivel: int
    area: str                       # Gerencia | Comercial | Judicial | Sistema | Integración
    tipo: str = "persona"           # persona | sistema | integracion
    colaborador_id: Optional[str] = None


SISTEMA = Actor(id="sistema", nombre="Sistema", nivel=1, area="Sistema", tipo="sistema")
INTEGRACION = Actor(id="integracion", nombre="Integración (API)", nivel=1, area="Integración", tipo="integracion")

# Lo que un sistema externo (CRM, banco, RR.HH.) puede hacer con su clave de servicio.
COMANDOS_INTEGRACION = {
    "estado", "caso", "escanear", "actualizar-caso", "ingresar-aviso", "conciliar-planilla",
    "crear-caso", "importar-casos", "registrar-ausencia", "extraer-comprobante", "registrar-tratamiento",
}
# Cualquier persona con sesión.
COMANDOS_LIBRES = {"estado", "caso", "escanear", "ingresar-aviso", "extraer-comprobante", "registrar-tratamiento",
                   "leer-notificaciones", "sesion"}

CAMPOS_POR_AREA = {
    "Comercial": {"estado_comercial"},
    "Judicial": {"estado_judicial", "fecha_diligencia"},
}
TITULAR_POR_AREA = {"Comercial": "responsable_comercial", "Judicial": "responsable_judicial"}

# Personas jurídicas: RUT desde 50.000.000. Sus datos no son datos personales (la ley protege a personas naturales).
RUT_MINIMO_EMPRESA = 50_000_000
OCULTO = "(oculto)"


def actor_desde(repo: Repositorio, valor: Optional[str]) -> Actor:
    if not valor:
        return SISTEMA
    if valor == INTEGRACION.id:
        return INTEGRACION
    usuario = repo.buscar("usuarios", valor)
    if not usuario or not usuario.get("activo", True):
        raise PermisoDenegado("La sesión no es válida: vuelva a iniciar sesión")
    return Actor(id=usuario["id"], nombre=usuario["nombre"], nivel=usuario["nivel"], area=usuario["area"],
                 colaborador_id=usuario.get("colaborador_id"))


def _exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise PermisoDenegado(mensaje)


# --- Reglas por acción ----------------------------------------------------------------

def casos_propios(repo: Repositorio, actor: Actor) -> Set[str]:
    """Casos donde la persona es titular o tiene (o tuvo) una tarea asignada."""
    if not actor.colaborador_id:
        return set()
    propios = {c["id"] for c in repo.listar("casos")
               if actor.colaborador_id in (c["responsable_comercial"], c["responsable_judicial"])}
    propios |= {t["caso_id"] for t in repo.listar("tareas") if t.get("responsable_id") == actor.colaborador_id}
    return propios


def campos_editables(repo: Repositorio, actor: Actor, caso: Dict[str, Any], propios: Optional[Set[str]] = None) -> List[str]:
    if actor.nivel == 1:
        return sorted(set().union(*CAMPOS_POR_AREA.values(), TITULAR_POR_AREA.values()))
    campos = set(CAMPOS_POR_AREA.get(actor.area, ()))
    if actor.nivel == 2:
        campos.add(TITULAR_POR_AREA[actor.area])
    elif caso["id"] not in (propios if propios is not None else casos_propios(repo, actor)):
        return []
    return sorted(campos)


def puede_atender(actor: Actor, tarea: Dict[str, Any]) -> bool:
    if tarea["estado"] != "Pendiente":
        return False
    return (actor.nivel == 1 or (actor.nivel == 2 and tarea["area"] == actor.area)
            or (actor.colaborador_id is not None and tarea.get("responsable_id") == actor.colaborador_id))


def puede_reasignar(actor: Actor, tarea: Dict[str, Any]) -> bool:
    return tarea["estado"] == "Pendiente" and (actor.nivel == 1 or (actor.nivel == 2 and tarea["area"] == actor.area))


def puede_gestionar_colaborador(actor: Actor, colaborador: Dict[str, Any]) -> bool:
    return actor.nivel == 1 or (actor.nivel == 2 and colaborador["area"] == actor.area)


def puede_registrar_ausencia(actor: Actor, colaborador: Dict[str, Any]) -> bool:
    return puede_gestionar_colaborador(actor, colaborador) or colaborador["id"] == actor.colaborador_id


def autorizar(repo: Repositorio, actor: Actor, comando: str, datos: Dict[str, Any]) -> None:
    """Lanza PermisoDenegado si el actor no puede ejecutar el comando con esos datos."""
    if actor.tipo == "sistema":
        return
    if actor.tipo == "integracion":
        _exigir(comando in COMANDOS_INTEGRACION, f"La clave de integración no permite «{comando}»")
        return
    if comando in COMANDOS_LIBRES:
        return
    nivel = actor.nivel
    if comando in ("crear-caso", "importar-casos"):
        _exigir(nivel <= 2, "Crear o importar casos corresponde a la gerencia (niveles 1 y 2)")
    elif comando == "actualizar-caso":
        caso = repo.obtener("casos", datos["caso_id"])
        permitidos = set(campos_editables(repo, actor, caso))
        _exigir(bool(permitidos), "Solo puede actualizar los casos que lleva")
        prohibidos = set(datos.get("cambios") or {}) - permitidos
        _exigir(not prohibidos, f"Su cargo no puede modificar: {', '.join(sorted(prohibidos))}")
    elif comando == "conciliar-planilla":
        _exigir(nivel == 1 or actor.area == "Comercial", "La conciliación de planillas corresponde al área Comercial")
    elif comando == "atender-tarea":
        tarea = repo.obtener("tareas", datos["tarea_id"])
        _exigir(puede_atender(actor, tarea), "Solo puede atender sus propias tareas pendientes")
    elif comando == "reasignar-tarea":
        tarea = repo.obtener("tareas", datos["tarea_id"])
        _exigir(puede_reasignar(actor, tarea), "Reasignar tareas corresponde a la gerencia del área")
    elif comando == "disponibilidad":
        colaborador = repo.obtener("colaboradores", datos["colaborador_id"])
        _exigir(puede_gestionar_colaborador(actor, colaborador), "Solo la gerencia del área cambia la disponibilidad")
    elif comando == "registrar-ausencia":
        colaborador = repo.obtener("colaboradores", datos["colaborador_id"])
        _exigir(puede_registrar_ausencia(actor, colaborador), "Solo puede informar sus propias ausencias")
    elif comando in ("exportar", "reiniciar"):
        _exigir(nivel == 1, "Esta acción corresponde a la gerencia general")
    else:
        raise PermisoDenegado(f"Acción no permitida: {comando}")


def permisos_generales(actor: Actor) -> Dict[str, bool]:
    nivel, persona = actor.nivel, actor.tipo == "persona"
    return {
        "crear_casos": nivel <= 2,
        "importar_casos": nivel <= 2,
        "conciliar_planillas": nivel == 1 or actor.area == "Comercial",
        "reasignar_tareas": nivel <= 2,
        "gestionar_equipo": nivel <= 2,
        "exportar": nivel == 1,
        "reiniciar_sandbox": nivel == 1 and persona,
        "ver_tratamientos": nivel == 1,
        "ver_todos_los_correos": nivel == 1,
    }


# --- Vista de los datos ---------------------------------------------------------------

def _es_empresa(rut: str) -> bool:
    numero = re.sub(r"\D", "", (rut or "").split("-")[0])
    return bool(numero) and int(numero) >= RUT_MINIMO_EMPRESA


def _iniciales(nombre: str) -> str:
    return " ".join(f"{p[0]}." for p in nombre.split() if p)


def _datos_sensibles(caso: Dict[str, Any]) -> Dict[str, str]:
    """Textos del caso que identifican a una persona natural, con su reemplazo."""
    deudor, bien = caso["deudor"], caso["bien_garantia"]
    reemplazos = {}
    if not _es_empresa(deudor.get("rut")):
        reemplazos[deudor["nombre"]] = _iniciales(deudor["nombre"])
        reemplazos[deudor["rut"]] = OCULTO
    for valor in (deudor.get("email"), deudor.get("telefono")):
        if valor:
            reemplazos[valor] = OCULTO
    if bien.get("patente"):
        reemplazos[bien["patente"]] = OCULTO
    return {k: v for k, v in reemplazos.items() if k}


def _reemplazar(objeto: Any, reemplazos: Dict[str, str]) -> Any:
    if not reemplazos:
        return objeto
    patron = re.compile("|".join(re.escape(k) for k in sorted(reemplazos, key=len, reverse=True)))

    def recorrer(valor):
        if isinstance(valor, str):
            return patron.sub(lambda m: reemplazos[m.group(0)], valor)
        if isinstance(valor, dict):
            return {k: recorrer(v) for k, v in valor.items()}
        if isinstance(valor, list):
            return [recorrer(v) for v in valor]
        return valor
    return recorrer(objeto)


def _motivos_ausencia_ajenos(repo: Repositorio, actor: Actor) -> Dict[str, str]:
    """El motivo de una ausencia (p. ej. una licencia médica) es un dato sensible del colaborador."""
    motivos = {}
    for c in repo.listar("colaboradores"):
        if c["id"] == actor.colaborador_id:
            continue
        for motivo in [c.get("motivo_no_disponible")] + [a.get("motivo") for a in c.get("ausencias", [])]:
            if motivo:
                motivos[motivo] = "motivo reservado"
    return motivos


def _ocultar_caso(caso: Dict[str, Any]) -> Dict[str, Any]:
    reemplazos = _datos_sensibles(caso)
    oculto = _reemplazar(caso, reemplazos)
    oculto["deudor"] = {**oculto["deudor"], "email": OCULTO if caso["deudor"].get("email") else "",
                        "telefono": OCULTO if caso["deudor"].get("telefono") else ""}
    oculto["restringido"] = True
    return oculto


def _ocultar_aviso(aviso: Dict[str, Any], reemplazos: Dict[str, str]) -> Dict[str, Any]:
    oculto = _reemplazar(aviso, reemplazos)
    extraidos = dict(oculto.get("datos_extraidos") or {})
    for campo in ("rut_depositante", "nombre_depositante"):
        if extraidos.get(campo) and reemplazos:
            extraidos[campo] = OCULTO
    oculto["datos_extraidos"] = extraidos
    return oculto


def sesion_de(repo: Repositorio, actor: Actor) -> Dict[str, Any]:
    usuario = repo.buscar("usuarios", actor.id) if actor.tipo == "persona" else None
    return {
        "usuario": publico(usuario) if usuario else {"id": actor.id, "nombre": actor.nombre, "nivel": actor.nivel, "area": actor.area},
        "permisos": permisos_generales(actor),
    }


def vista_para(repo: Repositorio, actor: Actor, estado: Dict[str, Any]) -> Dict[str, Any]:
    """Adapta el estado completo a quien consulta: permisos, notificaciones y datos visibles."""
    vista = dict(estado)
    usuario = repo.buscar("usuarios", actor.id) if actor.tipo == "persona" else None
    vista["sesion"] = sesion_de(repo, actor)
    notificaciones = [n for n in repo.listar("notificaciones") if n["usuario_id"] == actor.id]
    vista["notificaciones"] = list(reversed(notificaciones))[:50]
    vista["notificaciones_sin_leer"] = sum(1 for n in notificaciones if not n["leida"])
    correos = repo.listar("correos")
    if actor.nivel != 1 and usuario:
        correos = [c for c in correos if c["para"] == usuario["email"]]
    vista["correos"] = list(reversed(correos))[:100] if (actor.nivel == 1 or usuario) else []

    if actor.nivel != 1:
        vista["tratamientos"] = []
        vista["historial"] = [h for h in estado["historial"] if h["area"] != "Protección de datos"]

    propios = casos_propios(repo, actor)
    vista["tareas"] = [{**t, "permisos": {"atender": puede_atender(actor, t), "reasignar": puede_reasignar(actor, t)}}
                       for t in estado["tareas"]]
    vista["colaboradores"] = [
        {**c, "permisos": {"gestionar": puede_gestionar_colaborador(actor, c), "ausencia": puede_registrar_ausencia(actor, c)}}
        for c in estado["colaboradores"]
    ]
    vista["casos"] = [{**c, "campos_editables": campos_editables(repo, actor, c, propios), "propio": c["id"] in propios}
                      for c in estado["casos"]]

    if actor.nivel == 3:
        vista = _ocultar_para_nivel_3(repo, actor, vista, propios)
    return vista


def _ocultar_para_nivel_3(repo: Repositorio, actor: Actor, vista: Dict[str, Any], propios: Set[str]) -> Dict[str, Any]:
    ajenos = {c["id"]: _datos_sensibles(c) for c in repo.listar("casos") if c["id"] not in propios}
    motivos = _motivos_ausencia_ajenos(repo, actor)
    # Fuera de un caso (p. ej. el historial general) se ocultan los datos de todos los casos ajenos,
    # salvo los que también aparecen en un caso propio (mismo deudor en dos causas).
    textos_propios = {k for c in repo.listar("casos") if c["id"] in propios for k in _datos_sensibles(c)}
    global_ = {k: v for r in ajenos.values() for k, v in r.items() if k not in textos_propios}

    def por_caso(registro):
        return {**ajenos.get(registro.get("caso_id"), {}), **motivos}

    vista["casos"] = [_ocultar_caso(c) if c["id"] in ajenos else c for c in vista["casos"]]
    vista["avisos"] = [_ocultar_aviso(a, ajenos[a["caso_id"]]) if a["caso_id"] in ajenos else a for a in vista["avisos"]]
    vista["eventos"] = [_reemplazar(e, por_caso(e)) for e in vista["eventos"]]
    vista["tareas"] = [_reemplazar(t, por_caso(t)) for t in vista["tareas"]]
    vista["historial"] = [
        _reemplazar(h, {**global_, **motivos}) for h in vista["historial"]
        if h.get("caso_id") in propios or h["usuario"] == actor.nombre
    ]
    colaboradores = []
    for c in vista["colaboradores"]:
        if c["id"] != actor.colaborador_id:
            c = copy.deepcopy(c)
            if c.get("motivo_no_disponible"):
                c["motivo_no_disponible"] = "motivo reservado"
            for a in c.get("ausencias", []):
                a["motivo"] = "Ausencia programada"
        colaboradores.append(c)
    vista["colaboradores"] = colaboradores
    return vista


def caso_para(repo: Repositorio, actor: Actor, detalle: Dict[str, Any]) -> Dict[str, Any]:
    """Detalle de un caso (GET /casos/:id) con la misma regla de ocultamiento."""
    caso_id = detalle["caso"]["id"]
    if actor.nivel != 3 or caso_id in casos_propios(repo, actor):
        return detalle
    reemplazos = {**_datos_sensibles(detalle["caso"]), **_motivos_ausencia_ajenos(repo, actor)}
    return {
        "caso": _ocultar_caso(detalle["caso"]),
        "avisos": [_ocultar_aviso(a, reemplazos) for a in detalle["avisos"]],
        "eventos": _reemplazar(detalle["eventos"], reemplazos),
        "tareas": _reemplazar(detalle["tareas"], reemplazos),
        "historial": [],
    }
