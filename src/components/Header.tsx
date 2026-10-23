import React from 'react';
import {
  ShieldAlert,
  Scale,
  Briefcase,
  Sparkles,
  FileSpreadsheet,
  Terminal,
  Activity,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Car,
} from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  metrics: {
    eventosCriticosActivos: number;
    alertasJudicialesPendientes: number;
    ahorroEstimadoCLP: number;
    casosConIncautacionActiva: number;
  };
  onResetData: () => void;
  onOpenNewNoticeModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  metrics,
  onResetData,
  onOpenNewNoticeModal,
}) => {
  const hasCriticalSeizureRisk = metrics.alertasJudicialesPendientes > 0;

  return (
    <header className="border-b border-slate-800 bg-slate-950/90 backdrop-blur sticky top-0 z-40">
      {/* Top Critical Risk Warning Banner if active unhandled seizure threat exists */}
      {hasCriticalSeizureRisk && (
        <div className="bg-gradient-to-r from-red-600 via-rose-600 to-amber-600 text-white px-4 py-2 shadow-md">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2 text-sm font-medium">
            <div className="flex items-center gap-2">
              <span className="flex h-3 w-3 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-white"></span>
              </span>
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>
                <strong>ALERTA CRÍTICA COBGESTION:</strong> Existe comprobante informado pendiente en causa con{' '}
                <strong>Orden de Incautación Vigente</strong> (Vehículo). Requiere acción judicial inmediata para evitar
                pérdida de <strong>$600.000 CLP</strong> en costas judiciales.
              </span>
            </div>
            <button
              onClick={() => setActiveTab('eventos')}
              className="bg-white/20 hover:bg-white/30 text-white text-xs font-semibold px-3 py-1 rounded transition flex items-center gap-1 shrink-0"
            >
              Atender Alerta Inmediata &rarr;
            </button>
          </div>
        </div>
      )}

      {/* Main Header Row */}
      <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 text-white font-black text-xl">
            C
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold tracking-tight text-white">Cobgestion</span>
              <span className="text-xs bg-indigo-500/20 text-indigo-300 font-semibold px-2 py-0.5 rounded border border-indigo-500/30">
                LegalTech
              </span>
              <span className="text-xs bg-emerald-500/20 text-emerald-300 font-medium px-2 py-0.5 rounded border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Motor Python v3.10
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Sistema Integrado de Detección de Eventos Críticos & Coordinación Judicial-Comercial
            </p>
          </div>
        </div>

        {/* Live Counters */}
        <div className="flex items-center gap-3 text-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 flex items-center gap-2">
            <Car className="w-4 h-4 text-amber-400" />
            <div>
              <p className="text-slate-400 text-[10px] uppercase font-bold">Pérdidas Prevenidas</p>
              <p className="text-emerald-400 font-bold text-sm">
                ${metrics.ahorroEstimadoCLP.toLocaleString('es-CL')} CLP
              </p>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            <div>
              <p className="text-slate-400 text-[10px] uppercase font-bold">Eventos Críticos</p>
              <p className="text-rose-400 font-bold text-sm">
                {metrics.eventosCriticosActivos} activos
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <button
            onClick={onOpenNewNoticeModal}
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-3.5 py-2 rounded-lg text-xs flex items-center gap-1.5 shadow-md shadow-indigo-600/30 transition cursor-pointer"
          >
            <Sparkles className="w-4 h-4" />
            Ingresar Comprobante (IA)
          </button>

          <button
            onClick={onResetData}
            title="Restablecer caso demostrativo del auto"
            className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto text-sm border-t border-slate-800/80 pt-1">
        <button
          onClick={() => setActiveTab('eventos')}
          className={`flex items-center gap-2 px-3.5 py-2 border-b-2 font-medium text-xs md:text-sm whitespace-nowrap transition cursor-pointer ${
            activeTab === 'eventos'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          Centro de Eventos Críticos
          {metrics.eventosCriticosActivos > 0 && (
            <span className="bg-rose-500/30 text-rose-300 text-[11px] font-bold px-1.5 py-0.2 rounded-full border border-rose-500/50">
              {metrics.eventosCriticosActivos}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('judicial')}
          className={`flex items-center gap-2 px-3.5 py-2 border-b-2 font-medium text-xs md:text-sm whitespace-nowrap transition cursor-pointer ${
            activeTab === 'judicial'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <Scale className="w-4 h-4" />
          Área Judicial (Causas & Diligencias)
          {metrics.alertasJudicialesPendientes > 0 && (
            <span className="bg-amber-500/30 text-amber-300 text-[11px] font-bold px-1.5 py-0.2 rounded-full border border-amber-500/50">
              {metrics.alertasJudicialesPendientes} urgentes
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('comercial')}
          className={`flex items-center gap-2 px-3.5 py-2 border-b-2 font-medium text-xs md:text-sm whitespace-nowrap transition cursor-pointer ${
            activeTab === 'comercial'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <Briefcase className="w-4 h-4" />
          Área Comercial (Avisos de Pago)
        </button>

        <button
          onClick={() => setActiveTab('mandantes')}
          className={`flex items-center gap-2 px-3.5 py-2 border-b-2 font-medium text-xs md:text-sm whitespace-nowrap transition cursor-pointer ${
            activeTab === 'mandantes'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" />
          Planillas Mandantes (Conciliación Batch)
        </button>

        <button
          onClick={() => setActiveTab('python')}
          className={`flex items-center gap-2 px-3.5 py-2 border-b-2 font-medium text-xs md:text-sm whitespace-nowrap transition cursor-pointer ${
            activeTab === 'python'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <Terminal className="w-4 h-4" />
          Motor Python & CLI
        </button>

        <button
          onClick={() => setActiveTab('trazabilidad')}
          className={`flex items-center gap-2 px-3.5 py-2 border-b-2 font-medium text-xs md:text-sm whitespace-nowrap transition cursor-pointer ${
            activeTab === 'trazabilidad'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <Activity className="w-4 h-4" />
          Dashboard & Auditoría
        </button>
      </div>
    </header>
  );
};
