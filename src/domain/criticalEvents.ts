import {
  Caso,
  AvisoPago,
  EventoCritico,
  TareaParalela,
  EstadoPago,
  AccionJudicial,
  PagoConciliado,
} from './types.js';

export const COSTO_INCAUTACION_PREVENIDO_CLP = 600000;

/**
 * Evaluates whether a new or updated payment notice triggers a Critical Event.
 * Rule from Cobgestion:
 * When a payment notice is received (even unverified), immediately generate a Critical Event
 * and trigger a Judicial Alert so the judicial area can suspend upcoming seizures or embargoes,
 * avoiding the 600.000 CLP real-world mistake.
 */
export function generateCriticalEventFromNotice(
  caso: Caso,
  aviso: AvisoPago,
  currentTime: string = new Date().toISOString()
): {
  evento: EventoCritico;
  tareaComercial: TareaParalela;
  tareaJudicial: TareaParalela;
} {
  const isHighRiskCase =
    caso.estadoJudicial === 'Orden de incautación vigente' ||
    caso.estadoJudicial === 'Diligencia con receptor programada' ||
    caso.estadoJudicial === 'Mandamiento de embargo' ||
    caso.bienEnGarantia.tipo === 'Vehículo';

  const prioridad = isHighRiskCase ? 'CRITICA' : 'ALTA';
  const riesgoFinancieroCLP = isHighRiskCase ? COSTO_INCAUTACION_PREVENIDO_CLP : 0;

  const eventoId = `EVT-${Math.floor(1000 + Math.random() * 9000)}`;

  // Deadlines: High risk cases get 4 business hours for judicial, 24 hours for commercial.
  const plazoJudicial = isHighRiskCase ? '4 horas (URGENTE)' : '24 horas';
  const plazoComercial = '24 horas';

  const evento: EventoCritico = {
    id: eventoId,
    casoId: caso.id,
    avisoPagoId: aviso.id,
    tipo: 'Pago informado pendiente de verificación',
    fechaDeteccion: currentTime,
    prioridad,
    estado: 'En gestión paralela',
    alertaJudicialGenerada: true,
    alertaComercialGenerada: true,
    riesgoFinancieroCLP,
    cerrado: false,
  };

  const tareaComercial: TareaParalela = {
    id: `TSK-COM-${Math.floor(100 + Math.random() * 900)}`,
    eventoCriticoId: eventoId,
    casoId: caso.id,
    area: 'Comercial',
    titulo: 'Verificar comprobante y conciliar pago',
    descripcion: `Verificar comprobante #${aviso.id} por $${aviso.montoInformado.toLocaleString('es-CL')} informado vía ${aviso.canal} contra cartola o planilla del mandante ${caso.mandante}.`,
    responsable: caso.responsableComercial,
    fechaCreacion: currentTime,
    plazoLimite: plazoComercial,
    estado: 'Pendiente',
  };

  const judicialTitle = isHighRiskCase
    ? 'URGENTE: Suspender orden de incautación de vehículo / embargo'
    : 'Revisar estado procesal y evaluar suspensión cautelar';

  const judicialDesc = isHighRiskCase
    ? `ALERTA PREVENTIVA: Se informó comprobante por $${aviso.montoInformado.toLocaleString('es-CL')}. Causa ${caso.rolCausa} en ${caso.tribunal} tiene orden de incautación vigente sobre vehículo (${caso.bienEnGarantia.patente || caso.bienEnGarantia.descripcion}). Suspender inmediatamente con receptor judicial para evitar costos de incautación indebida (~$600.000).`
    : `Analizar impacto del comprobante informado en causa ${caso.rolCausa} (${caso.tribunal}). Determinar si procede solicitar suspensión o prórroga de términos.`;

  const tareaJudicial: TareaParalela = {
    id: `TSK-JUD-${Math.floor(100 + Math.random() * 900)}`,
    eventoCriticoId: eventoId,
    casoId: caso.id,
    area: 'Judicial',
    titulo: judicialTitle,
    descripcion: judicialDesc,
    responsable: caso.responsableJudicial,
    fechaCreacion: currentTime,
    plazoLimite: plazoJudicial,
    estado: 'Pendiente',
  };

  return { evento, tareaComercial, tareaJudicial };
}

/**
 * Evaluates if a Critical Event can be closed.
 * CRITICAL RULE: A Critical Event cannot be closed simply because Commercial confirmed the payment.
 * BOTH areas (Commercial and Judicial) MUST complete their tasks or record their resolution.
 */
export function canCloseCriticalEvent(
  evento: EventoCritico,
  tareasDelEvento: TareaParalela[]
): { canClose: boolean; reason?: string } {
  const tareaComercial = tareasDelEvento.find((t) => t.area === 'Comercial');
  const tareaJudicial = tareasDelEvento.find((t) => t.area === 'Judicial');

  if (!tareaComercial || !tareaJudicial) {
    return {
      canClose: false,
      reason: 'El evento no cuenta con las dos tareas paralelas requeridas.',
    };
  }

  const comercialCompletada =
    tareaComercial.estado === 'Completada' || Boolean(evento.resolucionComercial);
  const judicialCompletada =
    tareaJudicial.estado === 'Completada' || Boolean(evento.resolucionJudicial);

  if (!comercialCompletada && !judicialCompletada) {
    return {
      canClose: false,
      reason: 'Ambas tareas (Comercial y Judicial) se encuentran pendientes.',
    };
  }

  if (comercialCompletada && !judicialCompletada) {
    return {
      canClose: false,
      reason:
        'El pago está verificado por Comercial, pero el área Judicial NO ha suspendido la causa ni cerrado su tarea. Existe riesgo inminente de incautación!',
    };
  }

  if (!comercialCompletada && judicialCompletada) {
    return {
      canClose: false,
      reason:
        'El área Judicial tomó acción preventiva, pero el área Comercial aún no confirma ni observa el pago.',
    };
  }

  return { canClose: true };
}

/**
 * Reconciles a payment notice against a Mandante batch sheet record.
 */
export function reconcileWithMandanteRecord(
  aviso: AvisoPago,
  mandanteRecord: {
    monto: number;
    codigoOperacion?: string;
    rut?: string;
    fecha?: string;
  }
): {
  isMatch: boolean;
  nuevoEstado: EstadoPago;
  diferenciaMonto: number;
  observacion: string;
} {
  const diff = aviso.montoInformado - mandanteRecord.monto;

  if (Math.abs(diff) < 1) {
    // Exact amount match
    const opMatch =
      !aviso.datosExtraidos.numeroOperacion ||
      !mandanteRecord.codigoOperacion ||
      aviso.datosExtraidos.numeroOperacion.trim().toLowerCase() ===
        mandanteRecord.codigoOperacion.trim().toLowerCase();

    if (opMatch) {
      return {
        isMatch: true,
        nuevoEstado: 'confirmado',
        diferenciaMonto: 0,
        observacion: 'Pago conciliado exitosamente contra planilla del mandante.',
      };
    }
  }

  return {
    isMatch: false,
    nuevoEstado: 'observado',
    diferenciaMonto: diff,
    observacion:
      diff !== 0
        ? `Discrepancia en monto informado ($${aviso.montoInformado.toLocaleString('es-CL')}) vs planilla mandante ($${mandanteRecord.monto.toLocaleString('es-CL')}). Diferencia: $${Math.abs(diff).toLocaleString('es-CL')}`
        : 'Discrepancia en código de operación o RUT no coincidente.',
  };
}

/**
 * Computes dashboard KPIs and metrics.
 */
export function computeDashboardMetrics(
  casos: Caso[],
  eventos: EventoCritico[],
  tareas: TareaParalela[],
  avisos: AvisoPago[]
) {
  const totalCasos = casos.length;
  const casosConIncautacionActiva = casos.filter(
    (c) => c.estadoJudicial === 'Orden de incautación vigente'
  ).length;

  const eventosCriticosActivos = eventos.filter((e) => !e.cerrado);
  const eventosCriticosCerrados = eventos.filter((e) => e.cerrado);

  const alertasJudicialesPendientes = eventos.filter(
    (e) => !e.cerrado && !e.resolucionJudicial
  ).length;

  const avisosPorConfirmar = avisos.filter(
    (a) => a.estadoVerificacion === 'informado'
  ).length;

  const avisosConfirmados = avisos.filter(
    (a) => a.estadoVerificacion === 'confirmado'
  ).length;

  const avisosObservados = avisos.filter(
    (a) => a.estadoVerificacion === 'observado'
  ).length;

  // Total CLP losses prevented by timely critical event suspension:
  // Count how many events in high risk vehicle cases reached suspension/preventive resolution
  const eventosConSuspensionOportuna = eventos.filter(
    (e) =>
      e.resolucionJudicial?.accionEjecutada === 'Suspender tramitación de incautación' ||
      e.resolucionJudicial?.accionEjecutada === 'Notificar receptor judicial' ||
      e.resolucionJudicial?.accionEjecutada === 'Levantar encargo judicial'
  ).length;

  const ahorroEstimadoCLP = eventosConSuspensionOportuna * COSTO_INCAUTACION_PREVENIDO_CLP;

  // Average time calculations or completion rate
  const totalTareasJudiciales = tareas.filter((t) => t.area === 'Judicial');
  const tareasJudicialesCompletadas = totalTareasJudiciales.filter(
    (t) => t.estado === 'Completada'
  ).length;

  const tasaCumplimientoJudicial =
    totalTareasJudiciales.length > 0
      ? Math.round((tareasJudicialesCompletadas / totalTareasJudiciales.length) * 100)
      : 100;

  return {
    totalCasos,
    casosConIncautacionActiva,
    eventosCriticosActivos: eventosCriticosActivos.length,
    eventosCriticosCerrados: eventosCriticosCerrados.length,
    alertasJudicialesPendientes,
    avisosPorConfirmar,
    avisosConfirmados,
    avisosObservados,
    eventosConSuspensionOportuna,
    ahorroEstimadoCLP,
    tasaCumplimientoJudicial,
  };
}
