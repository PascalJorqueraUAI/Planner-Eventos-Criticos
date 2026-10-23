export type EstadoPago = 'informado' | 'confirmado' | 'observado';

export type PrioridadEvento = 'CRITICA' | 'ALTA' | 'MEDIA' | 'BAJA';

export type EstadoEvento = 'Abierto' | 'En gestión paralela' | 'Cerrado coordinado';

export type EstadoTarea = 'Pendiente' | 'En revisión' | 'Completada' | 'Vencida';

export type AccionJudicial = 
  | 'Suspender tramitación de incautación'
  | 'Notificar receptor judicial'
  | 'Levantar encargo judicial'
  | 'Mantener curso ordinario'
  | 'Termino de causa por pago'
  | 'Revisión preventiva de medidas cautelares';

export interface Caso {
  id: string;
  rolCausa: string;
  tribunal: string;
  deudor: {
    nombre: string;
    rut: string;
    email: string;
    telefono: string;
    direccion?: string;
  };
  mandante: string;
  montoDeudaTotal: number;
  montoDemandado: number;
  bienEnGarantia: {
    tipo: 'Vehículo' | 'Inmueble' | 'Bienes Muebles' | 'Sin garantía';
    descripcion: string;
    patente?: string;
    valorAproxCLP: number;
  };
  estadoComercial: 'En negociación' | 'Acuerdo vigente' | 'Sin contacto' | 'Convenio incumplido' | 'Pagado';
  estadoJudicial: 
    | 'Demanda presentada'
    | 'Notificado'
    | 'Mandamiento de embargo'
    | 'Orden de incautación vigente'
    | 'Diligencia con receptor programada'
    | 'Suspendido preventivo por aviso de pago'
    | 'Suspendido formalmente en tribunal'
    | 'Terminado por pago';
  responsableComercial: string;
  responsableJudicial: string;
  fechaDiligenciaInminente?: string;
  fechaCreacion: string;
}

export interface AvisoPago {
  id: string;
  casoId: string;
  fechaRecepcion: string;
  montoInformado: number;
  origen: 
    | 'Pantallazo cliente (WhatsApp)' 
    | 'Correo cliente' 
    | 'Transferencia bancaria (Aviso automático)' 
    | 'Comprobante Servipag/CajaVecina' 
    | 'Planilla Mandante';
  canal: 'WhatsApp' | 'Email' | 'Portal Deudor' | 'Planilla Mandante';
  estadoVerificacion: EstadoPago;
  datosExtraidos: {
    bancoOrigen?: string;
    bancoDestino?: string;
    numeroOperacion?: string;
    rutDepositante?: string;
    nombreDepositante?: string;
    fechaHoraOperacion?: string;
    comentario?: string;
    confianzaIA?: number;
  };
  archivoComprobante?: {
    nombre: string;
    tipo: 'image' | 'text' | 'pdf';
    url?: string;
    previewText?: string;
  };
  observacionesComerciales?: string;
  observacionesJudiciales?: string;
}

export interface EventoCritico {
  id: string;
  casoId: string;
  avisoPagoId?: string;
  tipo: 
    | 'Pago informado pendiente de verificación'
    | 'Pago confirmado por mandante'
    | 'Pago observado con discrepancia'
    | 'Riesgo inminente de incautación'
    | 'Incumplimiento de acuerdo';
  fechaDeteccion: string;
  prioridad: PrioridadEvento;
  estado: EstadoEvento;
  alertaJudicialGenerada: boolean;
  alertaComercialGenerada: boolean;
  riesgoFinancieroCLP: number;
  resolucionComercial?: {
    fecha: string;
    usuario: string;
    estadoFinalPago: EstadoPago;
    observaciones: string;
  };
  resolucionJudicial?: {
    fecha: string;
    usuario: string;
    accionEjecutada: AccionJudicial;
    escritoPresentado?: boolean;
    observaciones: string;
  };
  cerrado: boolean;
  fechaCierre?: string;
}

export interface TareaParalela {
  id: string;
  eventoCriticoId: string;
  casoId: string;
  area: 'Comercial' | 'Judicial';
  titulo: string;
  descripcion: string;
  responsable: string;
  fechaCreacion: string;
  plazoLimite: string;
  estado: EstadoTarea;
  resolucion?: string;
  fechaResolucion?: string;
}

export interface PagoConciliado {
  id: string;
  casoId: string;
  avisoPagoId?: string;
  montoConciliado: number;
  codigoPlanillaMandante: string;
  mandante: string;
  fechaLiquidacion: string;
  fechaConciliacion: string;
  conciliadoPor: string;
  notas?: string;
}

export interface AuditoriaHistorial {
  id: string;
  casoId: string;
  eventoCriticoId?: string;
  timestamp: string;
  usuario: string;
  area: 'Comercial' | 'Judicial' | 'Sistema IA' | 'Mandante';
  accion: string;
  detalles: string;
}
