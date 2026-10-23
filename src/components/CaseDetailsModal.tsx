import React from 'react';
import {
  X,
  Scale,
  Car,
  Briefcase,
  AlertTriangle,
  FileText,
  DollarSign,
  User,
  Phone,
  Mail,
  MapPin,
  Clock,
  CheckCircle,
} from 'lucide-react';
import { Caso, EventoCritico, AvisoPago, TareaParalela } from '../domain/types.js';

interface CaseDetailsModalProps {
  caso: Caso | null;
  eventos: EventoCritico[];
  avisos: AvisoPago[];
  tareas: TareaParalela[];
  onClose: () => void;
  onOpenEscrito?: (caso: Caso) => void;
}

export const CaseDetailsModal: React.FC<CaseDetailsModalProps> = ({
  caso,
  eventos,
  avisos,
  tareas,
  onClose,
}) => {
  if (!caso) return null;

  const eventosDelCaso = eventos.filter((e) => e.casoId === caso.id);
  const avisosDelCaso = avisos.filter((a) => a.casoId === caso.id);
  const tareasDelCaso = tareas.filter((t) => t.casoId === caso.id);

  const hasVehicleRisk =
    caso.bienEnGarantia.tipo === 'Vehículo' &&
    (caso.estadoJudicial === 'Orden de incautación vigente' ||
      caso.estadoJudicial === 'Diligencia con receptor programada');

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 shadow-2xl my-auto">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                {caso.id}
              </span>
              <span className="text-xs font-semibold text-slate-400">&bull; Mandante: {caso.mandante}</span>
            </div>
            <h2 className="text-xl font-bold text-white mt-1">Causa ROL {caso.rolCausa}</h2>
            <p className="text-xs text-slate-400">{caso.tribunal}</p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Vehicle Alert if active */}
        {hasVehicleRisk && (
          <div className="mt-4 p-3.5 rounded-xl bg-red-950/60 border border-red-500/40 text-red-200 text-xs flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
            <div>
              <strong className="block text-white font-bold">
                ¡Orden de Incautación Vigente sobre Vehículo!
              </strong>
              <span>
                Existe riesgo inminente de ejecución por el receptor judicial. Toda recepción de aviso de pago
                debe comunicarse de forma urgente para evitar el costo de $600.000 CLP en incautación indebida.
              </span>
            </div>
          </div>
        )}

        {/* 3 Column Grid Info */}
        <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {/* Deudor Info */}
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
            <h4 className="font-bold text-slate-300 uppercase tracking-wider text-[10px] mb-2 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-indigo-400" />
              Datos del Deudor
            </h4>
            <p className="text-white font-bold text-sm">{caso.deudor.nombre}</p>
            <p className="text-indigo-400 font-mono mt-0.5">{caso.deudor.rut}</p>
            <p className="text-slate-400 mt-2 flex items-center gap-1">
              <Phone className="w-3 h-3 text-slate-500" /> {caso.deudor.telefono}
            </p>
            <p className="text-slate-400 flex items-center gap-1">
              <Mail className="w-3 h-3 text-slate-500" /> {caso.deudor.email}
            </p>
            {caso.deudor.direccion && (
              <p className="text-slate-400 mt-1 flex items-start gap-1">
                <MapPin className="w-3 h-3 text-slate-500 shrink-0 mt-0.5" />
                {caso.deudor.direccion}
              </p>
            )}
          </div>

          {/* Bien en Garantía */}
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
            <h4 className="font-bold text-slate-300 uppercase tracking-wider text-[10px] mb-2 flex items-center gap-1.5">
              <Car className="w-3.5 h-3.5 text-amber-400" />
              Garantía / Bien Embargable
            </h4>
            <p className="text-amber-200 font-bold text-sm">
              {caso.bienEnGarantia.patente ? `Patente ${caso.bienEnGarantia.patente}` : caso.bienEnGarantia.tipo}
            </p>
            <p className="text-slate-300 mt-1">{caso.bienEnGarantia.descripcion}</p>
            <p className="text-slate-400 mt-2">
              Tasación comercial estimada:{' '}
              <strong className="text-white">${caso.bienEnGarantia.valorAproxCLP.toLocaleString('es-CL')} CLP</strong>
            </p>
          </div>

          {/* Acreencia y Estados */}
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
            <h4 className="font-bold text-slate-300 uppercase tracking-wider text-[10px] mb-2 flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-cyan-400" />
              Estado Judicial & Comercial
            </h4>
            <div className="space-y-1.5">
              <div>
                <span className="text-slate-500 block text-[10px]">Monto Demandado:</span>
                <span className="text-emerald-400 font-bold text-base">
                  ${caso.montoDemandado.toLocaleString('es-CL')} CLP
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">Estado Judicial:</span>
                <span className="text-white font-semibold">{caso.estadoJudicial}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">Responsables:</span>
                <span className="text-slate-300">
                  Jud: {caso.responsableJudicial} &bull; Com: {caso.responsableComercial}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Associated Notices & Tasks */}
        <div className="mt-5 space-y-4">
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
            <h4 className="text-xs font-bold text-white mb-2 uppercase tracking-wider">
              Avisos y Comprobantes de Pago Asociados ({avisosDelCaso.length})
            </h4>
            {avisosDelCaso.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No hay comprobantes informados para este caso aún.</p>
            ) : (
              <div className="space-y-2">
                {avisosDelCaso.map((a) => (
                  <div
                    key={a.id}
                    className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between text-xs"
                  >
                    <div>
                      <p className="font-bold text-white">
                        ${a.montoInformado.toLocaleString('es-CL')} CLP{' '}
                        <span className="text-slate-400 font-normal">vía {a.canal}</span>
                      </p>
                      <p className="text-[11px] text-slate-400">
                        Op: {a.datosExtraidos.numeroOperacion || 'S/N'} &bull; Fecha:{' '}
                        {a.fechaRecepcion.slice(0, 16).replace('T', ' ')}
                      </p>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        a.estadoVerificacion === 'confirmado'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : a.estadoVerificacion === 'observado'
                          ? 'bg-amber-500/20 text-amber-400'
                          : 'bg-blue-500/20 text-blue-400'
                      }`}
                    >
                      {a.estadoVerificacion}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold cursor-pointer"
          >
            Cerrar Expediente
          </button>
        </div>
      </div>
    </div>
  );
};
