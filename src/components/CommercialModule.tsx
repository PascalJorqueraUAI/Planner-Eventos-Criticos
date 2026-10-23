import React, { useState } from 'react';
import {
  Briefcase,
  CheckCircle,
  AlertCircle,
  Clock,
  Eye,
  DollarSign,
  FileText,
  User,
  Building,
  Sparkles,
  HelpCircle,
  ExternalLink,
} from 'lucide-react';
import { Caso, AvisoPago, EventoCritico } from '../domain/types.js';

interface CommercialModuleProps {
  avisos: AvisoPago[];
  casos: Caso[];
  eventos: EventoCritico[];
  onResolveCommercial: (eventoId: string, nuevoEstado: 'confirmado' | 'observado', notas: string) => Promise<void>;
  onOpenNoticeModal: () => void;
  onSelectCase: (casoId: string) => void;
}

export const CommercialModule: React.FC<CommercialModuleProps> = ({
  avisos,
  casos,
  eventos,
  onResolveCommercial,
  onOpenNoticeModal,
  onSelectCase,
}) => {
  const [filtroEstado, setFiltroEstado] = useState<'todos' | 'informado' | 'confirmado' | 'observado'>('todos');
  const [selectedAviso, setSelectedAviso] = useState<AvisoPago | null>(null);
  const [modalAction, setModalAction] = useState<{
    aviso: AvisoPago;
    evento: EventoCritico;
    targetEstado: 'confirmado' | 'observado';
  } | null>(null);

  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const filteredAvisos = avisos.filter((a) => {
    if (filtroEstado === 'todos') return true;
    return a.estadoVerificacion === filtroEstado;
  });

  const handleOpenActionModal = (aviso: AvisoPago, targetEstado: 'confirmado' | 'observado') => {
    const evento = eventos.find((e) => e.avisoPagoId === aviso.id);
    if (!evento) {
      alert('No se encontró evento crítico activo para este comprobante');
      return;
    }
    setNotes(
      targetEstado === 'confirmado'
        ? 'Pago verificado contra cartola bancaria del día. Fondos acreditados conforme.'
        : 'Observación: El comprobante no registra sello de recepción o el monto difiere de la cuota acordada.'
    );
    setModalAction({ aviso, evento, targetEstado });
  };

  const handleConfirmAction = async () => {
    if (!modalAction) return;
    setSubmitting(true);
    try {
      await onResolveCommercial(modalAction.evento.id, modalAction.targetEstado, notes);
      setModalAction(null);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Briefcase className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Área Comercial & Conciliación de Pagos</h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Registro, verificación y conciliación de comprobantes recibidos de clientes, avisos bancarios y planillas
              comerciales.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onOpenNoticeModal}
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-3.5 py-2 rounded-xl text-xs flex items-center gap-1.5 shadow-md shadow-indigo-600/30 transition cursor-pointer"
          >
            <Sparkles className="w-4 h-4" />
            + Nuevo Comprobante
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 text-xs">
        <button
          onClick={() => setFiltroEstado('todos')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
            filtroEstado === 'todos' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:bg-slate-850'
          }`}
        >
          Todos ({avisos.length})
        </button>
        <button
          onClick={() => setFiltroEstado('informado')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 ${
            filtroEstado === 'informado'
              ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
              : 'text-slate-400 hover:bg-slate-800'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          Por Confirmar ({avisos.filter((a) => a.estadoVerificacion === 'informado').length})
        </button>
        <button
          onClick={() => setFiltroEstado('confirmado')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 ${
            filtroEstado === 'confirmado'
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
              : 'text-slate-400 hover:bg-slate-800'
          }`}
        >
          <CheckCircle className="w-3.5 h-3.5" />
          Confirmados ({avisos.filter((a) => a.estadoVerificacion === 'confirmado').length})
        </button>
        <button
          onClick={() => setFiltroEstado('observado')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 ${
            filtroEstado === 'observado'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'text-slate-400 hover:bg-slate-800'
          }`}
        >
          <AlertCircle className="w-3.5 h-3.5" />
          Observados / Discrepancias ({avisos.filter((a) => a.estadoVerificacion === 'observado').length})
        </button>
      </div>

      {/* Notices List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredAvisos.map((aviso) => {
          const caso = casos.find((c) => c.id === aviso.casoId);
          const evento = eventos.find((e) => e.avisoPagoId === aviso.id);

          return (
            <div
              key={aviso.id}
              className="bg-slate-900 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition shadow-md flex flex-col justify-between"
            >
              <div>
                {/* Header */}
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <span className="text-[11px] font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                      {aviso.id}
                    </span>
                    <h3 className="text-xl font-bold text-emerald-400 mt-1">
                      ${aviso.montoInformado.toLocaleString('es-CL')} CLP
                    </h3>
                    <p className="text-xs text-slate-400">
                      Recibido vía {aviso.canal} &bull; {aviso.fechaRecepcion.slice(0, 16).replace('T', ' ')}
                    </p>
                  </div>

                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase ${
                      aviso.estadoVerificacion === 'confirmado'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                        : aviso.estadoVerificacion === 'observado'
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                        : 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                    }`}
                  >
                    {aviso.estadoVerificacion === 'informado'
                      ? 'Por Confirmar'
                      : aviso.estadoVerificacion}
                  </span>
                </div>

                {/* Case & OCR Details */}
                {caso && (
                  <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800/80 mb-3 text-xs space-y-1.5">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Caso:</span>
                      <button
                        onClick={() => onSelectCase(caso.id)}
                        className="text-indigo-400 hover:text-indigo-300 font-bold flex items-center gap-1 cursor-pointer"
                      >
                        {caso.id} ({caso.rolCausa})
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Deudor:</span>
                      <strong className="text-white">{caso.deudor.nombre}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Mandante:</span>
                      <span className="text-slate-300">{caso.mandante}</span>
                    </div>
                  </div>
                )}

                {/* OCR Metadata Extracted */}
                <div className="bg-slate-950/40 p-3 rounded-xl border border-slate-800/50 mb-4 text-[11px] text-slate-300 space-y-1">
                  <p className="text-slate-400 text-[10px] font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-indigo-400" />
                    Datos Extraídos del Comprobante
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-slate-500 block">Banco Origen:</span>
                      <strong>{aviso.datosExtraidos.bancoOrigen || 'No detectado'}</strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block">N° Operación:</span>
                      <strong className="font-mono">{aviso.datosExtraidos.numeroOperacion || 'S/N'}</strong>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Depositante:</span>
                      <span>{aviso.datosExtraidos.nombreDepositante || aviso.datosExtraidos.rutDepositante || 'N/A'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Confianza Extracción:</span>
                      <span className="text-emerald-400 font-semibold">
                        {Math.round((aviso.datosExtraidos.confianzaIA || 0.95) * 100)}%
                      </span>
                    </div>
                  </div>

                  {aviso.archivoComprobante?.previewText && (
                    <div className="mt-2 pt-2 border-t border-slate-800/80 text-slate-400 italic">
                      &quot;{aviso.archivoComprobante.previewText}&quot;
                    </div>
                  )}

                  {aviso.observacionesComerciales && (
                    <div className="mt-2 pt-2 border-t border-slate-800 text-amber-300">
                      <strong className="block text-slate-400">Observaciones Comerciales:</strong>
                      {aviso.observacionesComerciales}
                    </div>
                  )}
                </div>
              </div>

              {/* Action buttons */}
              {evento && !evento.cerrado && aviso.estadoVerificacion === 'informado' ? (
                <div className="pt-3 border-t border-slate-800 grid grid-cols-2 gap-2">
                  <button
                    onClick={() => handleOpenActionModal(aviso, 'confirmado')}
                    className="bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 border border-emerald-500/40 text-xs font-semibold py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 transition cursor-pointer"
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    Confirmar Pago
                  </button>
                  <button
                    onClick={() => handleOpenActionModal(aviso, 'observado')}
                    className="bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 border border-amber-500/40 text-xs font-semibold py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 transition cursor-pointer"
                  >
                    <AlertCircle className="w-3.5 h-3.5" />
                    Observar Diferencia
                  </button>
                </div>
              ) : (
                <div className="pt-3 border-t border-slate-800 flex justify-between items-center text-xs text-slate-400">
                  <span>Estado: {aviso.estadoVerificacion.toUpperCase()}</span>
                  <span className="text-emerald-400 font-medium">Gestión comercial al día</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Confirmation / Observation Modal */}
      {modalAction && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-base font-bold text-white mb-1">
              {modalAction.targetEstado === 'confirmado' ? 'Confirmar Pago Recibido' : 'Observar Pago con Diferencias'}
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Comprobante #{modalAction.aviso.id} por ${modalAction.aviso.montoInformado.toLocaleString('es-CL')} CLP
            </p>

            <div className="space-y-3 text-xs mb-5">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Notas de Conciliación</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-slate-400 text-[11px]">
                Esta acción registrará la verificación en el motor Python de Cobgestion y actualizará la tarea comercial
                del Evento #{modalAction.evento.id}.
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setModalAction(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
              >
                Cancelar
              </button>
              <button
                disabled={submitting}
                onClick={handleConfirmAction}
                className={`px-4 py-2 rounded-lg text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-md ${
                  modalAction.targetEstado === 'confirmado'
                    ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/30'
                    : 'bg-amber-600 hover:bg-amber-500 shadow-amber-600/30'
                }`}
              >
                {submitting ? 'Procesando en Python...' : 'Confirmar Resolución'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
