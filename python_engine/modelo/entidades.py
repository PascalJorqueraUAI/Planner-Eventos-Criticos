"""
Entidades del dominio Cobgestion (capa Modelo).

El repositorio centralizado guarda cada entidad como un registro JSON (una "hoja"
de la planilla). Las dataclasses definen el esquema de cada hoja y se usan al
crear registros nuevos para garantizar que todos los campos existan.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# --- Catálogos de estados -------------------------------------------------------

ESTADOS_PAGO = ("informado", "confirmado", "observado")
ESTADOS_TAREA = ("Pendiente", "Atendida")
ESTADOS_EVENTO = ("Abierto", "Cerrado")

ESTADOS_COMERCIALES = (
    "En negociación",
    "Acuerdo vigente",
    "Sin contacto",
    "Convenio incumplido",
    "Pagado",
)

ESTADOS_JUDICIALES = (
    "Demanda presentada",
    "Notificado",
    "En tramitación",
    "Mandamiento de embargo",
    "Orden de incautación vigente",
    "Diligencia con receptor programada",
    "Suspendido preventivo por aviso de pago",
    "Suspendido formalmente en tribunal",
    "Terminado por pago",
)

# Estados judiciales con una medida de apremio en curso (embargo, incautación, receptor).
ESTADOS_JUDICIALES_APREMIO = (
    "Mandamiento de embargo",
    "Orden de incautación vigente",
    "Diligencia con receptor programada",
)

# Estados en que la causa ya no avanza y no requiere nuevas acciones de suspensión.
ESTADOS_JUDICIALES_CERRADOS = (
    "Suspendido formalmente en tribunal",
    "Terminado por pago",
)

AREAS = ("Comercial", "Judicial")

CARGOS = (
    "Ejecutivo Comercial",
    "Jefe Comercial",
    "Ejecutivo Judicial",
    "Jefe Judicial",
)

# Costo real asumido por Cobgestion en una incautación indebida (grúa, receptor, custodia y costas).
COSTO_INCAUTACION_INDEBIDA_CLP = 600000

FORMATO_FECHA = "%Y-%m-%dT%H:%M:%S"


def a_iso(momento: datetime) -> str:
    return momento.strftime(FORMATO_FECHA)


def desde_iso(texto: str) -> datetime:
    return datetime.fromisoformat(texto[:19])


# --- Entidades ------------------------------------------------------------------

@dataclass
class Caso:
    id: str
    rol_causa: str
    tribunal: str
    deudor: Dict[str, str]          # nombre, rut, email, telefono
    mandante: str
    monto_deuda: int
    bien_garantia: Dict[str, Any]   # tipo, descripcion, patente
    estado_comercial: str
    estado_judicial: str
    responsable_comercial: str      # id de Colaborador titular
    responsable_judicial: str       # id de Colaborador titular
    fecha_creacion: str
    ultima_actualizacion: str
    fecha_diligencia: Optional[str] = None


@dataclass
class AvisoPago:
    id: str
    caso_id: str
    fecha_recepcion: str
    monto: int
    origen: str                     # Pantallazo WhatsApp, correo cliente, aviso banco, planilla mandante...
    canal: str                      # WhatsApp, Email, Portal Deudor, Planilla Mandante, API Banco
    estado: str = "informado"       # informado | confirmado | observado
    datos_extraidos: Dict[str, Any] = field(default_factory=dict)
    observaciones: str = ""


@dataclass
class Colaborador:
    id: str
    nombre: str
    area: str
    cargo: str
    competencias: List[str]         # tipos de tarea que puede ejecutar
    capacidad_max: int              # tareas simultáneas
    tareas_externas: int = 0        # carga en curso informada por el CRM, fuera de este sistema
    disponible: bool = True
    motivo_no_disponible: str = ""
    ausencias: List[Dict[str, str]] = field(default_factory=list)   # [{desde, hasta, motivo}] calendario programado
    no_disponible_por_ausencia: bool = False   # True si la no disponibilidad la puso el calendario (y él la levanta)


@dataclass
class RegistroDesempeno:
    """Una tarea atendida en el pasado: base del historial usado por el asignador."""
    colaborador_id: str
    tipo_tarea: str
    fecha: str
    horas_resolucion: float
    cumplio_sla: bool
    tarea_id: Optional[str] = None


@dataclass
class EventoCritico:
    id: str
    codigo: str                     # código del catálogo (EC-01...)
    nombre: str
    caso_id: str
    prioridad: str                  # CRITICA | ALTA | MEDIA
    motivo: str                     # explicación de por qué se disparó la regla
    clave: str                      # evita detectar dos veces el mismo hecho
    fecha_deteccion: str
    aviso_id: Optional[str] = None
    estado: str = "Abierto"
    riesgo_clp: int = 0
    fecha_cierre: Optional[str] = None


@dataclass
class Tarea:
    id: str
    evento_id: str
    caso_id: str
    tipo: str
    area: str
    titulo: str
    descripcion: str
    prioridad: str
    sla_horas: int
    fecha_creacion: str
    fecha_limite: str
    estado: str = "Pendiente"
    responsable_id: Optional[str] = None
    raci: Dict[str, List[str]] = field(default_factory=dict)
    asignacion: Dict[str, Any] = field(default_factory=dict)
    resultado: Optional[str] = None
    notas: str = ""
    fecha_atencion: Optional[str] = None
    atendida_por: Optional[str] = None
    reasignaciones: int = 0
    fecha_asignacion: Optional[str] = None
    # 0 = con su responsable original · 1 = reasignada por vencimiento · 2 = escalada a jefatura
    nivel_escalamiento: int = 0
    plazo_escalamiento: Optional[str] = None   # plazo del responsable actual tras un escalamiento


@dataclass
class RegistroTratamiento:
    """
    Registro de una comunicación de datos personales a un tercero (encargado del tratamiento).
    Guarda qué se hizo y con qué resguardos, nunca el contenido enviado.
    """
    id: str
    timestamp: str
    usuario: str
    finalidad: str
    proveedor: str
    modelo: str
    ubicacion: str                  # dónde se procesan los datos (transferencia internacional)
    tipo_entrada: str               # "texto seudonimizado" | "imagen"
    categorias_datos: List[str]
    medidas: List[str]              # minimización, seudonimización, sin almacenamiento…
    hash_entrada: str               # SHA-256 del comprobante: permite trazar sin guardar el contenido
    resultado: str                  # "ok" | "error"


@dataclass
class RegistroHistorial:
    id: str
    timestamp: str
    usuario: str
    area: str                       # Comercial | Judicial | Sistema | Integración
    accion: str
    detalle: str
    entidad: str                    # Caso | Aviso | Evento | Tarea | Colaborador
    entidad_id: str
    caso_id: Optional[str] = None
    cambios: Dict[str, List[Any]] = field(default_factory=dict)   # campo -> [antes, después]
