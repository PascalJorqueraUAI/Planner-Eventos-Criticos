"""
Modelos de datos para el sistema de Cobgestion (LegalTech)
Estructura según definición de repositorio centralizado:
- Casos
- Avisos_Pago
- Pagos_Conciliados
- Eventos_Criticos
- Tareas
- Historial
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime

COSTO_INCAUTACION_PREVENIDO_CLP = 600000

@dataclass
class Deudor:
    nombre: str
    rut: str
    email: str
    telefono: str
    direccion: str = ""

@dataclass
class BienGarantia:
    tipo: str  # 'Vehículo', 'Inmueble', 'Bienes Muebles', 'Sin garantía'
    descripcion: str
    patente: Optional[str] = None
    valor_aprox_clp: int = 0

@dataclass
class Caso:
    id: str
    rol_causa: str
    tribunal: str
    deudor: Deudor
    mandante: str
    monto_deuda_total: int
    monto_demandado: int
    bien_en_garantia: BienGarantia
    estado_comercial: str  # 'En negociación', 'Acuerdo vigente', 'Sin contacto', 'Convenio incumplido', 'Pagado'
    estado_judicial: str   # 'Demanda presentada', 'Notificado', 'Mandamiento de embargo', 'Orden de incautación vigente', 'Diligencia con receptor programada', 'Suspendido preventivo por aviso de pago', 'Suspendido formalmente en tribunal', 'Terminado por pago'
    responsable_comercial: str
    responsable_judicial: str
    fecha_creacion: str
    fecha_diligencia_inminente: Optional[str] = None

@dataclass
class DatosExtraidos:
    banco_origen: Optional[str] = None
    banco_destino: Optional[str] = None
    numero_operacion: Optional[str] = None
    rut_depositante: Optional[str] = None
    nombre_depositante: Optional[str] = None
    fecha_hora_operacion: Optional[str] = None
    comentario: Optional[str] = None
    confianza_ia: float = 0.95

@dataclass
class ArchivoComprobante:
    nombre: str
    tipo: str  # 'image', 'text', 'pdf'
    url: Optional[str] = None
    preview_text: Optional[str] = None

@dataclass
class AvisoPago:
    id: str
    caso_id: str
    fecha_recepcion: str
    monto_informado: int
    origen: str  # 'Pantallazo cliente (WhatsApp)', 'Correo cliente', 'Transferencia bancaria (Aviso automático)', 'Comprobante Servipag/CajaVecina', 'Planilla Mandante'
    canal: str   # 'WhatsApp', 'Email', 'Portal Deudor', 'Planilla Mandante'
    estado_verificacion: str  # 'informado', 'confirmado', 'observado'
    datos_extraidos: DatosExtraidos = field(default_factory=DatosExtraidos)
    archivo_comprobante: Optional[ArchivoComprobante] = None
    observaciones_comerciales: str = ""
    observaciones_judiciales: str = ""

@dataclass
class TareaParalela:
    id: str
    evento_critico_id: str
    caso_id: str
    area: str  # 'Comercial', 'Judicial'
    titulo: str
    descripcion: str
    responsable: str
    fecha_creacion: str
    plazo_limite: str
    estado: str  # 'Pendiente', 'En revisión', 'Completada', 'Vencida'
    resolucion: Optional[str] = None
    fecha_resolucion: Optional[str] = None

@dataclass
class ResolucionComercial:
    fecha: str
    usuario: str
    estado_final_pago: str
    observaciones: str

@dataclass
class ResolucionJudicial:
    fecha: str
    usuario: str
    accion_ejecutada: str
    escrito_presentado: bool
    observaciones: str

@dataclass
class EventoCritico:
    id: str
    caso_id: str
    aviso_pago_id: Optional[str]
    tipo: str  # 'Pago informado pendiente de verificación', 'Pago confirmado por mandante', 'Pago observado con discrepancia', 'Riesgo inminente de incautación'
    fecha_deteccion: str
    prioridad: str  # 'CRITICA', 'ALTA', 'MEDIA'
    estado: str     # 'Abierto', 'En gestión paralela', 'Cerrado coordinado'
    alerta_judicial_generada: bool = True
    alerta_comercialGenerada: bool = True
    riesgo_financiero_clp: int = 0
    resolucion_comercial: Optional[ResolucionComercial] = None
    resolucion_judicial: Optional[ResolucionJudicial] = None
    cerrado: bool = False
    fecha_cierre: Optional[str] = None

@dataclass
class PagoConciliado:
    id: str
    caso_id: str
    aviso_pago_id: Optional[str]
    monto_conciliado: int
    codigo_planilla_mandante: str
    mandante: str
    fecha_liquidacion: str
    fecha_conciliacion: str
    conciliado_por: str
    notas: str = ""

@dataclass
class AuditoriaHistorial:
    id: str
    caso_id: str
    evento_critico_id: Optional[str]
    timestamp: str
    usuario: str
    area: str
    accion: str
    detalles: str
