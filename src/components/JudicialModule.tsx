import React, { useState } from 'react';
import {
  Scale,
  Car,
  AlertTriangle,
  FileCheck,
  Clock,
  ShieldCheck,
  Copy,
  Check,
  Building,
  User,
  ExternalLink,
  ChevronRight,
  Send,
  FileText,
} from 'lucide-react';
import { Caso, EventoCritico, AvisoPago } from '../domain/types.js';

interface JudicialModuleProps {
  casos: Caso[];
  eventos: EventoCritico[];
  avisos: AvisoPago[];
  onResolveJudicial: (eventoId: string, accion: string, escrito: boolean, notas: string) => Promise<void>;
  onSelectCase: (casoId: string) => void;
}

export const JudicialModule: React.FC<JudicialModuleProps> = ({
  casos,
  eventos,
  avisos,
  onResolveJudicial,
  onSelectCase,
}) => {
  const [selectedCaseForEscrito, setSelectedCaseForEscrito] = useState<Caso | null>(null);
  const [copied, setCopied] = useState(false);
  const [filtro, setFiltro] = useState<string>('todos');

  const filteredCasos = casos.filter((c) => {
    if (filtro === 'incautacion') return c.estadoJudicial === 'Orden de incautación vigente';
    if (filtro === 'suspendido') return c.estadoJudicial.includes('Suspendido');
    if (filtro === 'embargo') return c.estadoJudicial.includes('embargo');
    return true;
  });

  const generateEscritoText = (caso: Caso, aviso?: AvisoPago) => {
    const fechaHoy = new Date().toLocaleDateString('es-CL', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });

    const montoStr = aviso ? `$${aviso.montoInformado.toLocaleString('es-CL')} CLP` : '$[MONTO] CLP';
    const bienStr = caso.bienEnGarantia.patente
      ? `automóvil patente única ${caso.bienEnGarantia.patente} (${caso.bienEnGarantia.descripcion})`
      : caso.bienEnGarantia.descripcion;

    return `S.J.L. CIVIL DE SANTIAGO (${caso.tribunal.toUpperCase()})

EN LO PRINCIPAL: SE TENGA PRESENTE COMPROBANTE DE PAGO INFORMADO Y SE ORDENE LA SUSPENSIÓN PREVENTIVA DE LA DILIGENCIA DE INCAUTACIÓN / EMBARGO; EN EL PRIMER OTROSÍ: SE OFICIE A RECEPTOR JUDICIAL PARA EFECTOS DE FRENAR CUALQUIER ACTUACIÓN; EN EL SEGUNDO OTROSÍ: SE OTORGUE PLAZO PARA ACREDITAR CONCILIACIÓN DEFINITIVA.

${caso.responsableJudicial.toUpperCase()}, Abogado por la parte ejecutante en autos sobre juicio ejecutivo caratulados "${caso.mandante.toUpperCase()} / ${caso.deudor.nombre.toUpperCase()}", ROL ${caso.rolCausa}, a US. respetuosamente digo:

Que con fecha reciente, se ha tomado conocimiento de que la parte ejecutada don(a) ${caso.deudor.nombre}, RUT ${caso.deudor.rut}, ha hecho llegar a las oficinas de Cobgestion comprobante de pago por la suma de ${montoStr}, en el marco de las gestiones de regularización de su acreencia.

Atendido lo anterior, y con el fin de evitar actuaciones jurisdiccionales innecesarias y la generación de costas judiciales perjudiciales relativas a la diligencia sobre el ${bienStr}, vengo en solicitar a US. se sirva:

1. Tener presente el comprobante de pago acompañado;
2. Decretar la SUSPENSIÓN INMEDIATA de toda orden de incautación, retiro de especies, traba de embargo o remate actualmente vigentes en la presente causa;
3. Notificar de forma urgente al señor Receptor Judicial de turno para que se abstenga de practicar la diligencia programada.

POR TANTO;
A US. RUEGO, acceder a lo solicitado por ser de estricta justicia procesal.

PRIMER OTROSÍ: Ruego a US. ordenar la comunicación telefónica y electrónica urgente al Receptor Judicial a cargo de la diligencia de incautación de fecha próxima.
SEGUNDO OTROSÍ: Solicito un plazo prudencial de 15 días hábiles a efectos de acompañar la liquidación final conciliada con la institución mandante.

En Santiago de Chile, a ${fechaHoy}.`;
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Module Title Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <Scale className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Módulo Judicial & Control Procesal</h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Gestión de causas en tribunales, órdenes de incautación vigentes, control de receptores judiciales y
              suspensión oportuna para evitar perjuicios de $600.000 CLP.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setFiltro('todos')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition ${
              filtro === 'todos' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300'
            }`}
          >
            Todas las Causas ({casos.length})
          </button>
          <button
            onClick={() => setFiltro('incautacion')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition ${
              filtro === 'incautacion'
                ? 'bg-red-600 text-white'
                : 'bg-red-950/40 text-red-300 border border-red-500/30'
            }`}
          >
            Incautación Activa (Vehículos)
          </button>
          <button
            onClick={() => setFiltro('suspendido')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition ${
              filtro === 'suspendido'
                ? 'bg-emerald-600 text-white'
                : 'bg-emerald-950/40 text-emerald-300 border border-emerald-500/30'
            }`}
          >
            Suspendidos Preventivos
          </button>
        </div>
      </div>

      {/* Grid of Cases */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filteredCasos.map((caso) => {
          const eventosDelCaso = eventos.filter((e) => e.casoId === caso.id && !e.cerrado);
          const avisosDelCaso = avisos.filter((a) => a.casoId === caso.id);
          const hasActiveRisk =
            caso.estadoJudicial === 'Orden de incautación vigente' ||
            caso.estadoJudicial === 'Diligencia con receptor programada';

          const isSavedPreventively = caso.estadoJudicial.includes('Suspendido preventivo');

          return (
            <div
              key={caso.id}
              className={`bg-slate-900 border rounded-2xl p-5 transition shadow-md flex flex-col justify-between ${
                hasActiveRisk
                  ? 'border-red-500/60 shadow-red-950/20 bg-gradient-to-b from-slate-900 to-red-950/20'
                  : isSavedPreventively
                  ? 'border-emerald-500/40 bg-gradient-to-b from-slate-900 to-emerald-950/20'
                  : 'border-slate-800'
              }`}
            >
              <div>
                {/* Header */}
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                      {caso.id}
                    </span>
                    <h3 className="text-base font-bold text-white mt-1">Causa ROL {caso.rolCausa}</h3>
                    <p className="text-xs text-slate-400">{caso.tribunal}</p>
                  </div>

                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-bold flex items-center gap-1 ${
                      hasActiveRisk
                        ? 'bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse'
                        : isSavedPreventively
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {hasActiveRisk && <AlertTriangle className="w-3.5 h-3.5" />}
                    {isSavedPreventively && <ShieldCheck className="w-3.5 h-3.5" />}
                    {caso.estadoJudicial}
                  </span>
                </div>

                {/* Deudor & Mandante Details */}
                <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800/80 mb-3 space-y-2 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Deudor:</span>
                    <strong className="text-white">
                      {caso.deudor.nombre} ({caso.deudor.rut})
                    </strong>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Mandante:</span>
                    <span className="text-slate-200 font-medium">{caso.mandante}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Monto Demandado:</span>
                    <strong className="text-emerald-400">
                      ${caso.montoDemandado.toLocaleString('es-CL')} CLP
                    </strong>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Bien en Garantía:</span>
                    <span className="text-amber-300 font-bold flex items-center gap-1">
                      {caso.bienEnGarantia.tipo === 'Vehículo' && <Car className="w-3.5 h-3.5" />}
                      {caso.bienEnGarantia.patente ? `Patente ${caso.bienEnGarantia.patente}` : caso.bienEnGarantia.descripcion}
                    </span>
                  </div>
                </div>

                {/* Linked Payment Notices status */}
                {avisosDelCaso.length > 0 && (
                  <div className="mb-4">
                    <p className="text-[11px] text-slate-400 font-semibold mb-1 uppercase tracking-wider">
                      Comprobantes de Pago Registrados
                    </p>
                    {avisosDelCaso.map((av) => (
                      <div
                        key={av.id}
                        className="bg-indigo-950/30 border border-indigo-500/30 rounded-lg p-2.5 text-xs flex items-center justify-between"
                      >
                        <div>
                          <p className="text-white font-bold">
                            ${av.montoInformado.toLocaleString('es-CL')} CLP{' '}
                            <span className="text-indigo-300 text-[11px] font-normal">
                              ({av.origen})
                            </span>
                          </p>
                          <p className="text-slate-400 text-[10px]">
                            Op: {av.datosExtraidos.numeroOperacion || 'S/N'} &bull; Fecha: {av.fechaRecepcion.slice(0, 10)}
                          </p>
                        </div>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            av.estadoVerificacion === 'confirmado'
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : av.estadoVerificacion === 'observado'
                              ? 'bg-amber-500/20 text-amber-300'
                              : 'bg-blue-500/20 text-blue-300'
                          }`}
                        >
                          {av.estadoVerificacion}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Action buttons */}
              <div className="pt-3 border-t border-slate-800 flex flex-wrap items-center justify-between gap-2">
                <span className="text-[11px] text-slate-400">
                  Abogado: <strong className="text-slate-200">{caso.responsableJudicial}</strong>
                </span>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedCaseForEscrito(caso)}
                    className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition cursor-pointer"
                  >
                    <FileText className="w-3.5 h-3.5 text-indigo-400" />
                    Generar Escrito OJV
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal for Judicial Escrito Generator */}
      {selectedCaseForEscrito && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400">
                  <Scale className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">
                    Escrito Judicial Preventivo: Solicitud de Suspensión de Incautación
                  </h3>
                  <p className="text-xs text-slate-400">
                    Causa ROL {selectedCaseForEscrito.rolCausa} &bull; {selectedCaseForEscrito.tribunal}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedCaseForEscrito(null)}
                className="text-slate-400 hover:text-white text-lg font-bold p-1 cursor-pointer"
              >
                &times;
              </button>
            </div>

            <div className="my-4 overflow-y-auto flex-1 bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 whitespace-pre-wrap leading-relaxed select-all">
              {generateEscritoText(
                selectedCaseForEscrito,
                avisos.find((a) => a.casoId === selectedCaseForEscrito.id)
              )}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <p className="text-[11px] text-slate-400">
                Listo para cargar en la Oficina Judicial Virtual (OJV) de Chile.
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() =>
                    copyToClipboard(
                      generateEscritoText(
                        selectedCaseForEscrito,
                        avisos.find((a) => a.casoId === selectedCaseForEscrito.id)
                      )
                    )
                  }
                  className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 rounded-lg text-xs flex items-center gap-1.5 transition cursor-pointer shadow-md shadow-indigo-600/30"
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-300" /> : <Copy className="w-4 h-4" />}
                  {copied ? 'Copiado al Portapapeles!' : 'Copiar Escrito OJV'}
                </button>
                <button
                  onClick={() => setSelectedCaseForEscrito(null)}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-4 py-2 rounded-lg cursor-pointer"
                >
                  Cerrar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
