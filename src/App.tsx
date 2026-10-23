/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Header } from './components/Header.js';
import { CriticalEventsView } from './components/CriticalEventsView.js';
import { JudicialModule } from './components/JudicialModule.js';
import { CommercialModule } from './components/CommercialModule.js';
import { MandanteReconcileView } from './components/MandanteReconcileView.js';
import { PythonEngineConsole } from './components/PythonEngineConsole.js';
import { TraceabilityDashboard } from './components/TraceabilityDashboard.js';
import { UnstructuredIngestionModal } from './components/UnstructuredIngestionModal.js';
import { CaseDetailsModal } from './components/CaseDetailsModal.js';
import { Caso, EventoCritico, TareaParalela, AvisoPago, PagoConciliado, AuditoriaHistorial } from './domain/types.js';
import { computeDashboardMetrics } from './domain/criticalEvents.js';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('eventos');

  // State entities
  const [casos, setCasos] = useState<Caso[]>([]);
  const [eventos, setEventos] = useState<EventoCritico[]>([]);
  const [tareas, setTareas] = useState<TareaParalela[]>([]);
  const [avisos, setAvisos] = useState<AvisoPago[]>([]);
  const [pagosConciliados, setPagosConciliados] = useState<PagoConciliado[]>([]);
  const [historial, setHistorial] = useState<AuditoriaHistorial[]>([]);
  const [loading, setLoading] = useState(true);

  // Modals
  const [isNoticeModalOpen, setIsNoticeModalOpen] = useState(false);
  const [selectedCaseIdForModal, setSelectedCaseIdForModal] = useState<string | null>(null);

  // Fetch full state from server
  const fetchState = async () => {
    try {
      const resp = await fetch('/api/state');
      if (resp.ok) {
        const data = await resp.json();
        if (data) {
          // Normalize Python snake_case to TS camelCase if needed
          const normalizedCasos: Caso[] = (data.casos || []).map((c: any) => ({
            id: c.id,
            rolCausa: c.rol_causa || c.rolCausa,
            tribunal: c.tribunal,
            deudor: c.deudor,
            mandante: c.mandante,
            montoDeudaTotal: c.monto_deuda_total || c.montoDeudaTotal,
            montoDemandado: c.monto_demandado || c.montoDemandado,
            bienEnGarantia: {
              tipo: c.bien_en_garantia?.tipo || c.bienEnGarantia?.tipo,
              descripcion: c.bien_en_garantia?.descripcion || c.bienEnGarantia?.descripcion,
              patente: c.bien_en_garantia?.patente || c.bienEnGarantia?.patente,
              valorAproxCLP: c.bien_en_garantia?.valor_aprox_clp || c.bienEnGarantia?.valorAproxCLP || 0,
            },
            estadoComercial: c.estado_comercial || c.estadoComercial,
            estadoJudicial: c.estado_judicial || c.estadoJudicial,
            responsableComercial: c.responsable_comercial || c.responsableComercial,
            responsableJudicial: c.responsable_judicial || c.responsableJudicial,
            fechaCreacion: c.fecha_creacion || c.fechaCreacion,
            fechaDiligenciaInminente: c.fecha_diligencia_inminente || c.fechaDiligenciaInminente,
          }));

          const normalizedAvisos: AvisoPago[] = (data.avisos || []).map((a: any) => ({
            id: a.id,
            casoId: a.caso_id || a.casoId,
            fechaRecepcion: a.fecha_recepcion || a.fechaRecepcion,
            montoInformado: a.monto_informado || a.montoInformado,
            origen: a.origen,
            canal: a.canal,
            estadoVerificacion: a.estado_verificacion || a.estadoVerificacion,
            datosExtraidos: {
              bancoOrigen: a.datos_extraidos?.banco_origen || a.datosExtraidos?.bancoOrigen,
              bancoDestino: a.datos_extraidos?.banco_destino || a.datosExtraidos?.bancoDestino,
              numeroOperacion: a.datos_extraidos?.numero_operacion || a.datosExtraidos?.numeroOperacion,
              rutDepositante: a.datos_extraidos?.rut_depositante || a.datosExtraidos?.rutDepositante,
              nombreDepositante: a.datos_extraidos?.nombre_depositante || a.datosExtraidos?.nombreDepositante,
              fechaHoraOperacion: a.datos_extraidos?.fecha_hora_operacion || a.datosExtraidos?.fechaHoraOperacion,
              comentario: a.datos_extraidos?.comentario || a.datosExtraidos?.comentario,
              confianzaIA: a.datos_extraidos?.confianza_ia || a.datosExtraidos?.confianzaIA,
            },
            archivoComprobante: a.archivo_comprobante || a.archivoComprobante,
            observacionesComerciales: a.observaciones_comerciales || a.observacionesComerciales,
            observacionesJudiciales: a.observaciones_judiciales || a.observacionesJudiciales,
          }));

          const normalizedEventos: EventoCritico[] = (data.eventos || []).map((e: any) => ({
            id: e.id,
            casoId: e.caso_id || e.casoId,
            avisoPagoId: e.aviso_pago_id || e.avisoPagoId,
            tipo: e.tipo,
            fechaDeteccion: e.fecha_deteccion || e.fechaDeteccion,
            prioridad: e.prioridad,
            estado: e.estado,
            alertaJudicialGenerada: e.alerta_judicial_generada ?? e.alertaJudicialGenerada ?? true,
            alertaComercialGenerada: e.alerta_comercialGenerada ?? e.alertaComercialGenerada ?? true,
            riesgoFinancieroCLP: e.riesgo_financiero_clp || e.riesgoFinancieroCLP || 0,
            resolucionComercial: e.resolucion_comercial
              ? {
                  fecha: e.resolucion_comercial.fecha,
                  usuario: e.resolucion_comercial.usuario,
                  estadoFinalPago: e.resolucion_comercial.estado_final_pago || e.resolucion_comercial.estadoFinalPago,
                  observaciones: e.resolucion_comercial.observaciones,
                }
              : undefined,
            resolucionJudicial: e.resolucion_judicial
              ? {
                  fecha: e.resolucion_judicial.fecha,
                  usuario: e.resolucion_judicial.usuario,
                  accionEjecutada: e.resolucion_judicial.accion_ejecutada || e.resolucion_judicial.accionEjecutada,
                  escritoPresentado: e.resolucion_judicial.escrito_presentado ?? e.resolucion_judicial.escritoPresentado,
                  observaciones: e.resolucion_judicial.observaciones,
                }
              : undefined,
            cerrado: Boolean(e.cerrado),
            fechaCierre: e.fecha_cierre || e.fechaCierre,
          }));

          const normalizedTareas: TareaParalela[] = (data.tareas || []).map((t: any) => ({
            id: t.id,
            eventoCriticoId: t.evento_critico_id || t.eventoCriticoId,
            casoId: t.caso_id || t.casoId,
            area: t.area,
            titulo: t.titulo,
            descripcion: t.descripcion,
            responsable: t.responsable,
            fechaCreacion: t.fecha_creacion || t.fechaCreacion,
            plazoLimite: t.plazo_limite || t.plazoLimite,
            estado: t.estado,
            resolucion: t.resolucion,
            fechaResolucion: t.fecha_resolucion || t.fechaResolucion,
          }));

          const normalizedPagos: PagoConciliado[] = (data.pagos_conciliados || []).map((p: any) => ({
            id: p.id,
            casoId: p.caso_id || p.casoId,
            avisoPagoId: p.aviso_pago_id || p.avisoPagoId,
            montoConciliado: p.monto_conciliado || p.montoConciliado,
            codigoPlanillaMandante: p.codigo_planilla_mandante || p.codigoPlanillaMandante,
            mandante: p.mandante,
            fechaLiquidacion: p.fecha_liquidacion || p.fechaLiquidacion,
            fechaConciliacion: p.fecha_conciliacion || p.fechaConciliacion,
            conciliadoPor: p.conciliado_por || p.conciliadoPor,
            notas: p.notas,
          }));

          const normalizedHistorial: AuditoriaHistorial[] = (data.historial || []).map((h: any) => ({
            id: h.id,
            casoId: h.caso_id || h.casoId,
            eventoCriticoId: h.evento_critico_id || h.eventoCriticoId,
            timestamp: h.timestamp,
            usuario: h.usuario,
            area: h.area,
            accion: h.accion,
            detalles: h.detalles,
          }));

          setCasos(normalizedCasos);
          setAvisos(normalizedAvisos);
          setEventos(normalizedEventos);
          setTareas(normalizedTareas);
          setPagosConciliados(normalizedPagos);
          setHistorial(normalizedHistorial);
        }
      }
    } catch (err) {
      console.error('Error fetching state from backend:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchState();
  }, []);

  // Compute metrics
  const metrics = computeDashboardMetrics(casos, eventos, tareas, avisos);

  // Actions
  const handleResolveJudicial = async (eventoId: string, accion: string, escrito: boolean, notas: string) => {
    try {
      const resp = await fetch('/api/events/resolve-judicial', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          eventoId,
          accion,
          escrito,
          usuario: 'Abg. Rodrigo Morales',
          notas,
        }),
      });
      if (resp.ok) {
        await fetchState();
      }
    } catch (e) {
      console.error('Error resolving judicial:', e);
    }
  };

  const handleResolveCommercial = async (eventoId: string, estadoPago: 'confirmado' | 'observado', notas: string) => {
    try {
      const resp = await fetch('/api/events/resolve-commercial', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          eventoId,
          estadoPago,
          usuario: 'Camila Valenzuela',
          notas,
        }),
      });
      if (resp.ok) {
        await fetchState();
      }
    } catch (e) {
      console.error('Error resolving commercial:', e);
    }
  };

  const handleReconcileBatch = async (lote: any[]) => {
    try {
      const resp = await fetch('/api/mandante/reconcile-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lote,
          usuario: 'Sistema Batch Mandante',
        }),
      });
      const data = await resp.json();
      await fetchState();
      return data;
    } catch (e) {
      console.error('Error reconciling batch:', e);
      return null;
    }
  };

  const handleResetData = async () => {
    if (confirm('¿Restablecer datos del caso demostrativo a su estado inicial?')) {
      await fetch('/api/state/reset', { method: 'POST' });
      await fetchState();
      setActiveTab('eventos');
    }
  };

  const handleIngestComplete = async () => {
    await fetchState();
    setActiveTab('eventos');
  };

  const selectedCaso = casos.find((c) => c.id === selectedCaseIdForModal) || null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        metrics={metrics}
        onResetData={handleResetData}
        onOpenNewNoticeModal={() => setIsNoticeModalOpen(true)}
      />

      {/* Main Content Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6">
        {loading ? (
          <div className="py-24 text-center text-slate-400 text-sm">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            Cargando Repositorio Cobgestion & Conexión Motor Python...
          </div>
        ) : (
          <>
            {activeTab === 'eventos' && (
              <CriticalEventsView
                eventos={eventos}
                tareas={tareas}
                casos={casos}
                avisos={avisos}
                onResolveJudicial={handleResolveJudicial}
                onResolveCommercial={handleResolveCommercial}
                onViewCaseDetails={(casoId) => setSelectedCaseIdForModal(casoId)}
                onOpenNoticeModal={() => setIsNoticeModalOpen(true)}
              />
            )}

            {activeTab === 'judicial' && (
              <JudicialModule
                casos={casos}
                eventos={eventos}
                avisos={avisos}
                onResolveJudicial={handleResolveJudicial}
                onSelectCase={(casoId) => setSelectedCaseIdForModal(casoId)}
              />
            )}

            {activeTab === 'comercial' && (
              <CommercialModule
                avisos={avisos}
                casos={casos}
                eventos={eventos}
                onResolveCommercial={handleResolveCommercial}
                onOpenNoticeModal={() => setIsNoticeModalOpen(true)}
                onSelectCase={(casoId) => setSelectedCaseIdForModal(casoId)}
              />
            )}

            {activeTab === 'mandantes' && (
              <MandanteReconcileView
                pagosConciliados={pagosConciliados}
                avisos={avisos}
                casos={casos}
                onReconcileBatch={handleReconcileBatch}
              />
            )}

            {activeTab === 'python' && <PythonEngineConsole />}

            {activeTab === 'trazabilidad' && (
              <TraceabilityDashboard
                historial={historial}
                eventos={eventos}
                casos={casos}
                tareas={tareas}
                ahorroEstimadoCLP={metrics.ahorroEstimadoCLP}
              />
            )}
          </>
        )}
      </main>

      {/* Global Modals */}
      <UnstructuredIngestionModal
        casos={casos}
        isOpen={isNoticeModalOpen}
        onClose={() => setIsNoticeModalOpen(false)}
        onIngestComplete={handleIngestComplete}
      />

      <CaseDetailsModal
        caso={selectedCaso}
        eventos={eventos}
        avisos={avisos}
        tareas={tareas}
        onClose={() => setSelectedCaseIdForModal(null)}
      />

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 py-4 px-6 text-xs text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-2">
        <p>
          &copy; {new Date().getFullYear()} Cobgestion LegalTech SpA &bull; Sistema Integrado de Eventos Críticos &
          Gestión Paralela
        </p>
        <p className="flex items-center gap-2">
          <span>Python 3.10 Engine</span>
          <span>&bull;</span>
          <span>Dual-Track Tasking</span>
          <span>&bull;</span>
          <span>Cost Prevention Safeguard</span>
        </p>
      </footer>
    </div>
  );
}
