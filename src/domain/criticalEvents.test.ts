import test from 'node:test';
import assert from 'node:assert/strict';
import {
  generateCriticalEventFromNotice,
  canCloseCriticalEvent,
  reconcileWithMandanteRecord,
  computeDashboardMetrics,
  COSTO_INCAUTACION_PREVENIDO_CLP,
} from './criticalEvents.js';
import { Caso, AvisoPago, EventoCritico, TareaParalela } from './types.js';

const mockCasoVehiculo: Caso = {
  id: 'CASO-1052',
  rolCausa: 'C-1420-2026',
  tribunal: '17° Juzgado Civil de Santiago',
  deudor: {
    nombre: 'Carlos Silva Mendoza',
    rut: '16.482.910-K',
    email: 'carlos.silva@empresa.cl',
    telefono: '+56 9 8831 2290',
  },
  mandante: 'Forum Servicios Financieros',
  montoDeudaTotal: 4850000,
  montoDemandado: 4850000,
  bienEnGarantia: {
    tipo: 'Vehículo',
    descripcion: 'Automóvil Suzuki Swift 1.2 GLX',
    patente: 'BB-CL-44',
    valorAproxCLP: 6500000,
  },
  estadoComercial: 'En negociación',
  estadoJudicial: 'Orden de incautación vigente',
  responsableComercial: 'Camila Valenzuela',
  responsableJudicial: 'Abg. Rodrigo Morales',
  fechaCreacion: '2026-09-10T09:00:00',
};

const mockAviso: AvisoPago = {
  id: 'AVP-801',
  casoId: 'CASO-1052',
  fechaRecepcion: '2026-10-23T08:30:00',
  montoInformado: 850000,
  origen: 'Pantallazo cliente (WhatsApp)',
  canal: 'WhatsApp',
  estadoVerificacion: 'informado',
  datosExtraidos: {
    bancoOrigen: 'Banco de Chile',
    numeroOperacion: 'TRF-8849102',
    rutDepositante: '16.482.910-K',
  },
};

test('Detección inmediata de Evento Crítico ante aviso de pago no verificado', () => {
  const { evento, tareaComercial, tareaJudicial } = generateCriticalEventFromNotice(
    mockCasoVehiculo,
    mockAviso
  );

  assert.equal(evento.tipo, 'Pago informado pendiente de verificación');
  assert.equal(evento.prioridad, 'CRITICA');
  assert.equal(evento.riesgoFinancieroCLP, COSTO_INCAUTACION_PREVENIDO_CLP);
  assert.equal(evento.alertaJudicialGenerada, true);
  assert.equal(tareaComercial.area, 'Comercial');
  assert.equal(tareaJudicial.area, 'Judicial');
  assert.match(tareaJudicial.plazoLimite, /4 horas/);
});

test('Regla de Cobgestion: El evento NO se cierra solo con verificación comercial si Judicial no resolvió', () => {
  const { evento, tareaComercial, tareaJudicial } = generateCriticalEventFromNotice(
    mockCasoVehiculo,
    mockAviso
  );

  // Simular que Comercial completó su tarea
  tareaComercial.estado = 'Completada';
  evento.resolucionComercial = {
    fecha: new Date().toISOString(),
    usuario: 'Camila Valenzuela',
    estadoFinalPago: 'confirmado',
    observaciones: 'Comprobante verificado con éxito',
  };

  // Tarea judicial sigue pendiente
  tareaJudicial.estado = 'Pendiente';

  const check = canCloseCriticalEvent(evento, [tareaComercial, tareaJudicial]);
  assert.equal(check.canClose, false);
  assert.match(check.reason!, /Judicial NO ha suspendido/);
});

test('Cierre coordinado exitoso cuando ambas áreas completan sus tareas', () => {
  const { evento, tareaComercial, tareaJudicial } = generateCriticalEventFromNotice(
    mockCasoVehiculo,
    mockAviso
  );

  tareaComercial.estado = 'Completada';
  evento.resolucionComercial = {
    fecha: new Date().toISOString(),
    usuario: 'Camila Valenzuela',
    estadoFinalPago: 'confirmado',
    observaciones: 'OK',
  };

  tareaJudicial.estado = 'Completada';
  evento.resolucionJudicial = {
    fecha: new Date().toISOString(),
    usuario: 'Abg. Rodrigo Morales',
    accionEjecutada: 'Suspender tramitación de incautación',
    observaciones: 'Receptor notificado oportunamente',
  };

  const check = canCloseCriticalEvent(evento, [tareaComercial, tareaJudicial]);
  assert.equal(check.canClose, true);
});

test('Conciliación con planilla mandante detecta discrepancia de monto', () => {
  const resultado = reconcileWithMandanteRecord(mockAviso, {
    monto: 800000, // Informado era 850000 -> Diferencia 50.000
    codigoOperacion: 'TRF-8849102',
    rut: '16.482.910-K',
  });

  assert.equal(resultado.isMatch, false);
  assert.equal(resultado.nuevoEstado, 'observado');
  assert.equal(resultado.diferenciaMonto, 50000);
});

test('Cálculo de métricas de impacto previene $600.000 por caso suspendido', () => {
  const { evento, tareaComercial, tareaJudicial } = generateCriticalEventFromNotice(
    mockCasoVehiculo,
    mockAviso
  );
  evento.resolucionJudicial = {
    fecha: new Date().toISOString(),
    usuario: 'Abg. Rodrigo Morales',
    accionEjecutada: 'Suspender tramitación de incautación',
    observaciones: 'Incautación suspendida',
  };
  tareaJudicial.estado = 'Completada';

  const metrics = computeDashboardMetrics(
    [mockCasoVehiculo],
    [evento],
    [tareaComercial, tareaJudicial],
    [mockAviso]
  );

  assert.equal(metrics.ahorroEstimadoCLP, 600000);
  assert.equal(metrics.eventosConSuspensionOportuna, 1);
});
