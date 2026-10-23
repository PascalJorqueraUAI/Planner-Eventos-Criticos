import React, { useState } from 'react';
import {
  ShieldAlert,
  Clock,
  Car,
  AlertTriangle,
  CheckCircle,
  FileText,
  User,
  Calendar,
  DollarSign,
  ArrowRight,
  Info,
  Scale,
  Briefcase,
  ExternalLink,
  ShieldCheck,
  Building,
} from 'lucide-react';
import { Caso, EventoCritico, TareaParalela, AvisoPago } from '../domain/types.js';

interface CriticalEventsViewProps {
  eventos: EventoCritico[];
  tareas: TareaParalela[];
  casos: Caso[];
  avisos: AvisoPago[];
  onResolveJudicial: (eventoId: string, accion: string, escrito: boolean, notas: string) => Promise<void>;
  onResolveCommercial: (eventoId: string, nuevoEstado: 'confirmado' | 'observado', notas: string) => Promise<void>;
  onViewCaseDetails: (casoId: string) => void;
  onOpenNoticeModal: () => void;
}

export const CriticalEventsView: React.FC<CriticalEventsViewProps> = ({
  eventos,
  tareas,
  casos,
  avisos,
  onResolveJudicial,
  onResolveCommercial,
  onViewCaseDetails,
  onOpenNoticeModal,
}) => {
  const [filter, setFilter] = useState<'all' | 'active' | 'closed' | 'critical'>('active');
  const [selectedEventForModal, setSelectedEventForModal] = useState<EventoCritico | null>(null);
  const [modalType, setModalType] = useState<'judicial' | 'commercial' | null>(null);

  // Form states
  const [judicialAction, setJudicialAction] = useState<string>('Suspender tramitación de incautación');
  const [escritoPresentado, setEscritoPresentado] = useState<boolean>(true);
  const [judicialNotes, setJudicialNotes] = useState<string>(
    'Se contactó a receptor judicial para suspender diligencia programada sobre vehículo. Se prepara escrito de suspensión para el tribunal.'
  );

  const [commercialEstado, setCommercialEstado] = useState<'confirmado' | 'observado'>('confirmado');
  const [commercialNotes, setCommercialNotes] = useState<string>(
    'Comprobante verificado con cartola bancaria. Los fondos coinciden con el monto acordado.'
  );

  const [submitting, setSubmitting] = useState(false);

  // Filtered events
  const filteredEventos = eventos.filter((e) => {
    if (filter === 'active') return !e.cerrado;
    if (filter === 'closed') return e.cerrado;
    if (filter === 'critical') return e.prioridad === 'CRITICA';
    return true;
  });

  const handleOpenJudicialModal = (evento: EventoCritico) => {
    setSelectedEventForModal(evento);
    setModalType('judicial');
  };

  const handleOpenCommercialModal = (evento: EventoCritico) => {
    setSelectedEventForModal(evento);
    setModalType('commercial');
  };

  const submitJudicial = async () => {
    if (!selectedEventForModal) return;
    setSubmitting(true);
    try {
      await onResolveJudicial(
        selectedEventForModal.id,
        judicialAction,
        escritoPresentado,
        judicialNotes
      );
      setModalType(null);
      setSelectedEventForModal(null);
    } finally {
      setSubmitting(false);
    }
  };

  const submitCommercial = async () => {
    if (!selectedEventForModal) return;
    setSubmitting(true);
    try {
      await onResolveCommercial(
        selectedEventForModal.id,
        commercialEstado,
        commercialNotes
      );
      setModalType(null);
      setSelectedEventForModal(null);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner explaining the Capstone Real Scenario */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white">Detector de Eventos Críticos & Tareas Paralelas</h2>
                <span className="text-xs bg-indigo-500/20 text-indigo-300 font-semibold px-2 py-0.5 rounded border border-indigo-500/30">
                  Regla Cobgestion Activa
                </span>
              </div>
              <p className="text-slate-400 text-xs mt-1 max-w-3xl leading-relaxed">
                Todo aviso de pago recibido (aún sin conciliar) genera <strong>alerta inmediata</strong> y{' '}
                <strong>dos tareas simultáneas</strong>. El evento <strong>no se cierra</strong> hasta que{' '}
                <strong>ambas áreas</strong> (Comercial y Judicial) hayan registrado su resolución. Esto previene
                incautaciones erróneas y la pérdida de <strong>$600.000 CLP</strong> por falta de coordinación.
              </p>
            </div>
          </div>

          
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-2 mt-5 pt-4 border-t border-slate-800/80 text-xs">
          <span className="text-slate-400 font-medium">Filtrar eventos:</span>
          <button
            onClick={() => setFilter('active')}
            className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              filter === 'active'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                : 'text-slate-400 hover:bg-slate-800'
            }`}
          >
            Activos en Gestión
          </button>
          <button
            onClick={() => setFilter('critical')}
            className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              filter === 'critical'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                : 'text-slate-400 hover:bg-slate-800'
            }`}
          >
            Riesgo Crítico (Vehículos)
          </button>
          <button
            onClick={() => setFilter('closed')}
            className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              filter === 'closed'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                : 'text-slate-400 hover:bg-slate-800'
            }`}
          >
            Cerrados Coordinados
          </button>
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              filter === 'all'
                ? 'bg-slate-700 text-white'
                : 'text-slate-400 hover:bg-slate-800'
            }`}
          >
            Todos ({eventos.length})
          </button>
        </div>
      </div>

      {/* Events List */}
      <div className="space-y-4">
        {filteredEventos.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
            <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-3 opacity-80" />
            <h3 className="text-base font-bold text-white">No hay eventos en este estado</h3>
            <p className="text-slate-400 text-xs max-w-md mx-auto mt-1">
              Todos los eventos críticos han sido gestionados de manera coordinada por ambas áreas.
            </p>
          </div>
        ) : (
          filteredEventos.map((evento) => {
            const caso = casos.find((c) => c.id === evento.casoId);
            const aviso = avisos.find((a) => a.id === evento.avisoPagoId);
            const tareasDelEvento = tareas.filter((t) => t.eventoCriticoId === evento.id);
            const tareaComercial = tareasDelEvento.find((t) => t.area === 'Comercial');
            const tareaJudicial = tareasDelEvento.find((t) => t.area === 'Judicial');

            const isVehicleRisk =
              caso?.bienEnGarantia?.tipo === 'Vehículo' &&
              (caso?.estadoJudicial === 'Orden de incautación vigente' ||
                caso?.estadoJudicial === 'Diligencia con receptor programada');

            const comercialDone =
              tareaComercial?.estado === 'Completada' || Boolean(evento.resolucionComercial);
            const judicialDone =
              tareaJudicial?.estado === 'Completada' || Boolean(evento.resolucionJudicial);

            return (
              <div
                key={evento.id}
                className={`bg-slate-900 border rounded-2xl overflow-hidden transition shadow-lg ${
                  evento.prioridad === 'CRITICA' && !evento.cerrado
                    ? 'border-red-500/50 shadow-red-950/20'
                    : 'border-slate-800'
                }`}
              >
                {/* Event Card Header */}
                <div className="p-4 bg-slate-950/70 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span
                      className={`font-mono text-xs px-2.5 py-1 rounded-md font-bold ${
                        evento.prioridad === 'CRITICA'
                          ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                          : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                      }`}
                    >
                      {evento.prioridad === 'CRITICA' ? 'PRIORIDAD CRÍTICA' : 'PRIORIDAD ALTA'}
                    </span>
                    <span className="text-white font-bold text-sm tracking-wide">
                      Evento #{evento.id}
                    </span>
                    <span className="text-slate-400 text-xs">&bull;</span>
                    <span className="text-slate-300 text-xs font-semibold">
                      {evento.tipo}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {evento.cerrado ? (
                      <span className="bg-emerald-500/20 text-emerald-300 text-xs font-semibold px-2.5 py-1 rounded-full border border-emerald-500/30 flex items-center gap-1.5">
                        <CheckCircle className="w-3.5 h-3.5" />
                        Cerrado Coordinado (Ambas áreas OK)
                      </span>
                    ) : (
                      <span className="bg-amber-500/20 text-amber-300 text-xs font-semibold px-2.5 py-1 rounded-full border border-amber-500/30 flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 animate-pulse" />
                        En Gestión Paralela
                      </span>
                    )}

                    {evento.riesgoFinancieroCLP > 0 && (
                      <span className="bg-red-950/80 text-red-300 text-xs font-bold px-2.5 py-1 rounded-full border border-red-700/60 flex items-center gap-1">
                        <DollarSign className="w-3.5 h-3.5 text-red-400" />
                        Riesgo Costas: ${evento.riesgoFinancieroCLP.toLocaleString('es-CL')} CLP
                      </span>
                    )}
                  </div>
                </div>

                {/* Case & Notice Information Strip */}
                {caso && (
                  <div className="p-4 bg-slate-900/90 border-b border-slate-800/80 grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
                    <div>
                      <p className="text-slate-400 text-[11px] uppercase tracking-wider font-semibold">
                        Expediente Judicial
                      </p>
                      <button
                        onClick={() => onViewCaseDetails(caso.id)}
                        className="text-indigo-400 hover:text-indigo-300 font-bold text-sm flex items-center gap-1 mt-0.5 text-left cursor-pointer"
                      >
                        {caso.rolCausa} &bull; {caso.id}
                        <ExternalLink className="w-3 h-3" />
                      </button>
                      <p className="text-slate-400">{caso.tribunal}</p>
                    </div>

                    <div>
                      <p className="text-slate-400 text-[11px] uppercase tracking-wider font-semibold">
                        Deudor & Mandante
                      </p>
                      <p className="text-white font-medium text-sm mt-0.5">{caso.deudor.nombre}</p>
                      <p className="text-slate-400">
                        RUT: {caso.deudor.rut} &bull; Mandante: {caso.mandante}
                      </p>
                    </div>

                    <div>
                      <p className="text-slate-400 text-[11px] uppercase tracking-wider font-semibold">
                        Bien en Garantía
                      </p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        {caso.bienEnGarantia.tipo === 'Vehículo' && (
                          <Car className="w-4 h-4 text-amber-400 shrink-0" />
                        )}
                        <span className="text-amber-200 font-bold text-sm">
                          {caso.bienEnGarantia.patente
                            ? `Patente ${caso.bienEnGarantia.patente}`
                            : caso.bienEnGarantia.descripcion}
                        </span>
                      </div>
                      <p className="text-slate-400">
                        Estado judicial: <strong className="text-red-400">{caso.estadoJudicial}</strong>
                      </p>
                    </div>

                    {aviso && (
                      <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
                        <p className="text-slate-400 text-[10px] uppercase font-bold flex items-center justify-between">
                          <span>Comprobante Informado</span>
                          <span
                            className={`px-1.5 py-0.2 rounded font-bold text-[10px] uppercase ${
                              aviso.estadoVerificacion === 'confirmado'
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : aviso.estadoVerificacion === 'observado'
                                ? 'bg-amber-500/20 text-amber-400'
                                : 'bg-blue-500/20 text-blue-400'
                            }`}
                          >
                            {aviso.estadoVerificacion === 'informado'
                              ? 'Por Confirmar'
                              : aviso.estadoVerificacion}
                          </span>
                        </p>
                        <p className="text-emerald-400 font-bold text-base mt-0.5">
                          ${aviso.montoInformado.toLocaleString('es-CL')} CLP
                        </p>
                        <p className="text-slate-400 text-[11px] truncate">
                          Vía {aviso.canal} &bull; Op: {aviso.datosExtraidos.numeroOperacion || 'S/N'}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Cobgestion Safeguard Warning Bar if one is completed and the other is still pending */}
                {comercialDone && !judicialDone && !evento.cerrado && (
                  <div className="bg-red-950/80 border-b border-red-500/50 px-4 py-2.5 text-xs text-red-200 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                    <span>
                      <strong>PROTECCIÓN COBGESTION:</strong> Comercial verificó el pago, pero el evento{' '}
                      <strong>NO SE CIERRA</strong> porque Judicial aún no decreta la suspensión formal. ¡Si el receptor no
                      es notificado hoy, el auto será incautado por error con pérdida de $600.000 CLP!
                    </span>
                  </div>
                )}

                {/* Parallel Task Execution Split (2 Columns) */}
                <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Left Column: Tarea Comercial */}
                  <div
                    className={`rounded-xl p-4 border transition ${
                      comercialDone
                        ? 'bg-slate-950/40 border-emerald-500/30'
                        : 'bg-slate-950/80 border-indigo-500/30'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400">
                          <Briefcase className="w-4 h-4" />
                        </div>
                        <div>
                          <span className="text-[10px] text-indigo-400 font-bold tracking-wider uppercase">
                            Área Comercial
                          </span>
                          <h4 className="text-white font-bold text-sm">Verificar Pago & Conciliación</h4>
                        </div>
                      </div>

                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                          comercialDone
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                            : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
                        }`}
                      >
                        {comercialDone ? 'Completada' : 'En Revisión'}
                      </span>
                    </div>

                    <p className="text-slate-300 text-xs mb-3 leading-relaxed">
                      {tareaComercial?.descripcion ||
                        'Verificar comprobante informado contra cartola bancaria o planilla mandante.'}
                    </p>

                    <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 text-[11px] text-slate-400 space-y-1 mb-3">
                      <div className="flex justify-between">
                        <span>Responsable Comercial:</span>
                        <strong className="text-slate-200">
                          {tareaComercial?.responsable || caso?.responsableComercial}
                        </strong>
                      </div>
                      <div className="flex justify-between">
                        <span>Plazo de gestión (SLA):</span>
                        <strong className="text-slate-200">{tareaComercial?.plazoLimite || '24 horas'}</strong>
                      </div>
                      {evento.resolucionComercial && (
                        <div className="pt-1.5 border-t border-slate-800 text-emerald-300">
                          <span className="block font-semibold">Resolución Registrada:</span>
                          <span className="text-slate-300">
                            Pago {evento.resolucionComercial.estadoFinalPago.toUpperCase()}:{' '}
                            {evento.resolucionComercial.observaciones}
                          </span>
                        </div>
                      )}
                    </div>

                    {!comercialDone ? (
                      <button
                        onClick={() => handleOpenCommercialModal(evento)}
                        className="w-full bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/40 font-semibold py-2 px-3 rounded-lg text-xs transition flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        Registrar Verificación Comercial (Confirmar / Observar)
                      </button>
                    ) : (
                      <div className="text-emerald-400 text-xs flex items-center gap-1.5 font-medium py-1">
                        <CheckCircle className="w-4 h-4" />
                        Verificación comercial finalizada
                      </div>
                    )}
                  </div>

                  {/* Right Column: Tarea Judicial */}
                  <div
                    className={`rounded-xl p-4 border transition ${
                      judicialDone
                        ? 'bg-slate-950/40 border-emerald-500/30'
                        : isVehicleRisk
                        ? 'bg-red-950/20 border-red-500/40'
                        : 'bg-slate-950/80 border-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div
                          className={`p-1.5 rounded-lg ${
                            isVehicleRisk
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-amber-500/20 text-amber-400'
                          }`}
                        >
                          <Scale className="w-4 h-4" />
                        </div>
                        <div>
                          <span
                            className={`text-[10px] font-bold tracking-wider uppercase ${
                              isVehicleRisk ? 'text-red-400' : 'text-amber-400'
                            }`}
                          >
                            Área Judicial
                          </span>
                          <h4 className="text-white font-bold text-sm">
                            {isVehicleRisk
                              ? 'Urgente: Frenar Incautación de Vehículo'
                              : 'Revisar Estado & Suspender Gestiones'}
                          </h4>
                        </div>
                      </div>

                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                          judicialDone
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                            : isVehicleRisk
                            ? 'bg-red-500/20 text-red-400 border border-red-500/50 animate-pulse'
                            : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        }`}
                      >
                        {judicialDone ? 'Completada' : isVehicleRisk ? 'SLA 4 Horas URGENTE' : 'Pendiente'}
                      </span>
                    </div>

                    <p className="text-slate-300 text-xs mb-3 leading-relaxed">
                      {tareaJudicial?.descripcion ||
                        'Evaluar suspensión procesal preventiva para evitar perjuicio al deudor y costas a Cobgestion.'}
                    </p>

                    <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 text-[11px] text-slate-400 space-y-1 mb-3">
                      <div className="flex justify-between">
                        <span>Abogado Responsable:</span>
                        <strong className="text-slate-200">
                          {tareaJudicial?.responsable || caso?.responsableJudicial}
                        </strong>
                      </div>
                      <div className="flex justify-between">
                        <span>Plazo de reacción:</span>
                        <strong className={isVehicleRisk ? 'text-red-400 font-bold' : 'text-slate-200'}>
                          {tareaJudicial?.plazoLimite || '4 horas (URGENTE)'}
                        </strong>
                      </div>
                      {evento.resolucionJudicial && (
                        <div className="pt-1.5 border-t border-slate-800 text-emerald-300">
                          <span className="block font-semibold">Resolución Judicial Aplicada:</span>
                          <span className="text-slate-300">
                            {evento.resolucionJudicial.accionEjecutada} &bull;{' '}
                            {evento.resolucionJudicial.observaciones}
                          </span>
                        </div>
                      )}
                    </div>

                    {!judicialDone ? (
                      <button
                        onClick={() => handleOpenJudicialModal(evento)}
                        className={`w-full font-semibold py-2 px-3 rounded-lg text-xs transition flex items-center justify-center gap-1.5 cursor-pointer ${
                          isVehicleRisk
                            ? 'bg-red-600 hover:bg-red-500 text-white shadow-md shadow-red-600/30'
                            : 'bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 border border-amber-500/40'
                        }`}
                      >
                        <Scale className="w-3.5 h-3.5" />
                        Ejecutar Acción Judicial (Suspender Incautación / Notificar Receptor)
                      </button>
                    ) : (
                      <div className="text-emerald-400 text-xs flex items-center gap-1.5 font-medium py-1">
                        <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        Suspensión judicial ejecutada. Costas prevenidas ($600.000 CLP salvados)
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Modal: Acción Judicial */}
      {modalType === 'judicial' && selectedEventForModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl bg-red-500/20 text-red-400">
                <Scale className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Resolución de Tarea Judicial</h3>
                <p className="text-xs text-slate-400">
                  Evento #{selectedEventForModal.id} &bull; Causa {selectedEventForModal.casoId}
                </p>
              </div>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Acción Procesal a Ejecutar</label>
                <select
                  value={judicialAction}
                  onChange={(e) => setJudicialAction(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="Suspender tramitación de incautación">
                    Suspender tramitación de incautación de vehículo (Evita pérdida $600.000)
                  </option>
                  <option value="Notificar receptor judicial">
                    Notificar de urgencia a receptor judicial para suspender diligencia
                  </option>
                  <option value="Levantar encargo judicial">
                    Levantar encargo de búsqueda y apremio en tribunal
                  </option>
                  <option value="Mantener curso ordinario">
                    Mantener curso ordinario (Sin suspensión)
                  </option>
                  <option value="Termino de causa por pago">
                    Decretar término de causa por pago total
                  </option>
                </select>
              </div>

              <div className="flex items-center gap-2 bg-slate-950 p-3 rounded-xl border border-slate-800">
                <input
                  type="checkbox"
                  id="chkEscrito"
                  checked={escritoPresentado}
                  onChange={(e) => setEscritoPresentado(e.target.checked)}
                  className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500"
                >
                </input>
                <label htmlFor="chkEscrito" className="text-slate-300 font-medium cursor-pointer">
                  Generar e ingresar escrito de suspensión en Oficina Judicial Virtual (OJV)
                </label>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Observaciones / Instrucciones a Receptor
                </label>
                <textarea
                  value={judicialNotes}
                  onChange={(e) => setJudicialNotes(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                  placeholder="Detalles de la suspensión..."
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={() => setModalType(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
              >
                Cancelar
              </button>
              <button
                disabled={submitting}
                onClick={submitJudicial}
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-md shadow-red-600/30"
              >
                {submitting ? 'Procesando en Python...' : 'Confirmar Suspensión Judicial'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Acción Comercial */}
      {modalType === 'commercial' && selectedEventForModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl bg-indigo-500/20 text-indigo-400">
                <Briefcase className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Resolución de Tarea Comercial</h3>
                <p className="text-xs text-slate-400">
                  Evento #{selectedEventForModal.id} &bull; Verificación de Comprobante
                </p>
              </div>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Resultado de la Conciliación</label>
                <select
                  value={commercialEstado}
                  onChange={(e) => setCommercialEstado(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="confirmado">
                    Confirmado: Pago verificado contra cartola bancaria / planilla mandante
                  </option>
                  <option value="observado">
                    Observado / no confirmado: Existen diferencias de monto o antecedentes pendientes
                  </option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Notas de Verificación Comercial
                </label>
                <textarea
                  value={commercialNotes}
                  onChange={(e) => setCommercialNotes(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                  placeholder="Detalles de la cartola o diferencias detectadas..."
                />
              </div>

              <div className="bg-amber-500/10 border border-amber-500/30 p-3 rounded-xl text-amber-300 text-[11px] flex items-start gap-2">
                <Info className="w-4 h-4 shrink-0 mt-0.5" />
                <span>
                  Recordatorio Cobgestion: Marcar este pago como confirmado no cerrará el evento crítico si el área
                  Judicial todavía no suspende los apremios sobre la causa.
                </span>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={() => setModalType(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
              >
                Cancelar
              </button>
              <button
                disabled={submitting}
                onClick={submitCommercial}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-md shadow-indigo-600/30"
              >
                {submitting ? 'Procesando en Python...' : 'Guardar Resolución Comercial'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
