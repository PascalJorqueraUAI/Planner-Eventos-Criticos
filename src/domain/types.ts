/**
 * Tipos de la Vista. Reflejan 1:1 el JSON que entrega el motor Python
 * (python_engine/modelo/entidades.py), por eso conservan snake_case.
 */

export type EstadoPago = 'informado' | 'confirmado' | 'observado';
export type Prioridad = 'CRITICA' | 'ALTA' | 'MEDIA';
export type Area = 'Comercial' | 'Judicial';

export interface Caso {
  id: string;
  rol_causa: string;
  tribunal: string;
  deudor: { nombre: string; rut: string; email: string; telefono: string };
  mandante: string;
  monto_deuda: number;
  bien_garantia: { tipo: string; descripcion: string; patente?: string };
  estado_comercial: string;
  estado_judicial: string;
  responsable_comercial: string;
  responsable_judicial: string;
  fecha_creacion: string;
  ultima_actualizacion: string;
  fecha_diligencia: string | null;
}

export interface AvisoPago {
  id: string;
  caso_id: string;
  fecha_recepcion: string;
  monto: number;
  origen: string;
  canal: string;
  estado: EstadoPago;
  datos_extraidos: Record<string, any>;
  observaciones: string;
}

export interface EventoCritico {
  id: string;
  codigo: string;
  nombre: string;
  caso_id: string;
  aviso_id: string | null;
  prioridad: Prioridad;
  motivo: string;
  clave: string;
  fecha_deteccion: string;
  estado: 'Abierto' | 'Cerrado';
  riesgo_clp: number;
  fecha_cierre: string | null;
}

export interface Criterios {
  experiencia: number;
  desempeno: number;
  disponibilidad: number;
  continuidad: number;
}

export interface Asignacion {
  metodo: string;
  escalada: boolean;
  puntaje: number | null;
  criterios: Partial<Criterios>;
  pesos: Partial<Criterios>;
  candidatos: { id: string; nombre: string; puntaje: number; criterios: Criterios }[];
  excluidos: { id: string; nombre: string; motivo: string }[];
}

export interface Tarea {
  id: string;
  evento_id: string;
  caso_id: string;
  tipo: string;
  area: Area;
  titulo: string;
  descripcion: string;
  prioridad: Prioridad;
  sla_horas: number;
  fecha_creacion: string;
  fecha_limite: string;
  estado: 'Pendiente' | 'Atendida';
  responsable_id: string | null;
  raci: { R?: string[]; A?: string[]; C?: string[]; I?: string[] };
  asignacion: Asignacion;
  resultado: string | null;
  notas: string;
  fecha_atencion: string | null;
  atendida_por: string | null;
  reasignaciones: number;
  fecha_asignacion: string | null;
  /** 0 = responsable original · 1 = reasignada por vencimiento · 2 = escalada a jefatura */
  nivel_escalamiento: number;
  plazo_escalamiento: string | null;
  vencida: boolean;
}

export interface Ausencia {
  desde: string;
  hasta: string;
  motivo: string;
}

export interface PerfilHistorico {
  tareas: number;
  cumplidas_sla: number;
  tasa_sla: number | null;
  horas_promedio: number | null;
}

export interface Colaborador {
  id: string;
  nombre: string;
  area: Area;
  cargo: string;
  competencias: string[];
  capacidad_max: number;
  tareas_externas: number;
  disponible: boolean;
  motivo_no_disponible: string;
  ausencias: Ausencia[];
  no_disponible_por_ausencia: boolean;
  carga_actual: number;
  historico: PerfilHistorico;
  historico_por_tipo: Record<string, PerfilHistorico>;
}

export interface RegistroHistorial {
  id: string;
  timestamp: string;
  usuario: string;
  area: string;
  accion: string;
  detalle: string;
  entidad: string;
  entidad_id: string;
  caso_id: string | null;
  cambios: Record<string, [unknown, unknown]>;
}

export interface ReglaCatalogo {
  codigo: string;
  nombre: string;
  descripcion: string;
  condicion: string;
  ambito: 'aviso' | 'caso';
  prioridad_base: Prioridad;
  tareas: {
    tipo: string;
    area: Area;
    titulo: string;
    sla_horas: number;
    sla_horas_critica: number;
    resultados: string[];
  }[];
}

export interface Metricas {
  total_casos: number;
  casos_por_estado_judicial: Record<string, number>;
  casos_por_estado_comercial: Record<string, number>;
  avisos_por_estado: Record<string, number>;
  eventos_abiertos: number;
  eventos_criticos_abiertos: number;
  eventos_cerrados: number;
  eventos_por_codigo: Record<string, number>;
  tareas_pendientes: number;
  tareas_vencidas: number;
  tareas_atendidas: number;
  cumplimiento_sla_pct: number | null;
  horas_promedio_atencion: number | null;
  minutos_promedio_aviso_a_alerta: number | null;
  riesgo_expuesto_clp: number;
  riesgo_cubierto_clp: number;
  tareas_escaladas: number;
  tareas_escaladas_por_vencimiento: number;
  colaboradores: {
    id: string;
    nombre: string;
    area: Area;
    cargo: string;
    disponible: boolean;
    carga: number;
    capacidad: number;
    pendientes: number;
    vencidas: number;
    historico: PerfilHistorico;
  }[];
}

export interface EstadoSistema {
  ahora: string;
  casos: Caso[];
  avisos: AvisoPago[];
  eventos: EventoCritico[];
  tareas: Tarea[];
  colaboradores: Colaborador[];
  historial: RegistroHistorial[];
  catalogo: ReglaCatalogo[];
  matriz_raci: Record<string, Record<string, 'R' | 'A' | 'C' | 'I' | '-'>>;
  pesos_asignacion: Record<string, Criterios>;
  estados: { comercial: string[]; judicial: string[] };
  metricas: Metricas;
  ultimo_escaneo: string | null;
  extraccion: ConfigExtraccion;
  tratamientos: RegistroTratamiento[];
}

export interface ConfigExtraccion {
  gemini_activo: boolean;
  modelo: string;
  motivo: string;
}

/** Envío de datos personales a un encargado del tratamiento (sin el contenido). */
export interface RegistroTratamiento {
  id: string;
  timestamp: string;
  usuario: string;
  finalidad: string;
  proveedor: string;
  modelo: string;
  ubicacion: string;
  tipo_entrada: string;
  categorias_datos: string[];
  medidas: string[];
  hash_entrada: string;
  resultado: 'ok' | 'error';
}

export interface DatosExtraidos {
  monto: number;
  banco_origen: string | null;
  banco_destino?: string | null;
  numero_operacion: string | null;
  rut_depositante: string | null;
  nombre_depositante: string | null;
  fecha_hora_operacion?: string | null;
  comentario?: string | null;
  confianza: number | null;
  hash_comprobante: string;
  /** Texto exactamente como salió hacia Gemini (seudonimizado), o null si no salió nada. */
  datos_enviados: string | null;
  motor_extraccion: 'local' | 'Gemini';
  motivo: string;
}
