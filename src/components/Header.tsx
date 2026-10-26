import React from 'react';
import { AlertTriangle, Database, Radar, Users, BarChart3, RotateCcw } from 'lucide-react';
import type { Metricas } from '../domain/types.js';
import { clp } from './ui.js';

export type Modulo = 'repositorio' | 'detector' | 'asignacion' | 'dashboard';

const MODULOS: { id: Modulo; nombre: string; icono: React.ReactNode }[] = [
  { id: 'repositorio', nombre: 'Repositorio', icono: <Database className="w-4 h-4" /> },
  { id: 'detector', nombre: 'Detector de eventos', icono: <Radar className="w-4 h-4" /> },
  { id: 'asignacion', nombre: 'Asignación y seguimiento', icono: <Users className="w-4 h-4" /> },
  { id: 'dashboard', nombre: 'Trazabilidad', icono: <BarChart3 className="w-4 h-4" /> },
];

interface HeaderProps {
  activo: Modulo;
  onCambiar: (m: Modulo) => void;
  metricas: Metricas;
  onReiniciar: () => void;
}

export const Header: React.FC<HeaderProps> = ({ activo, onCambiar, metricas, onReiniciar }) => {
  const contadores: Partial<Record<Modulo, number>> = {
    detector: metricas.eventos_abiertos,
    asignacion: metricas.tareas_pendientes,
  };

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/85 backdrop-blur-xl sticky top-0 z-40">
      {metricas.eventos_criticos_abiertos > 0 && (
        <div className="bg-gradient-to-r from-red-700 via-rose-700 to-amber-700 text-white px-4 py-2">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2 text-xs sm:text-sm">
            <span className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>
                <strong>{metricas.eventos_criticos_abiertos} evento(s) crítico(s) abierto(s)</strong> en causas con apremio
                en curso · riesgo expuesto {clp(metricas.riesgo_expuesto_clp)}
                {metricas.tareas_vencidas > 0 && <> · <strong>{metricas.tareas_vencidas} tarea(s) vencida(s)</strong></>}
              </span>
            </span>
            <button
              onClick={() => onCambiar('asignacion')}
              className="bg-white/20 hover:bg-white/30 text-xs font-semibold px-3 py-1 rounded cursor-pointer"
            >
              Ver tareas →
            </button>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-white font-black">
            C
          </div>
          <div>
            <p className="text-base font-bold text-white leading-tight">Cobgestion · Eventos Críticos</p>
            <p className="text-[11px] text-slate-400">Coordinación Comercial–Judicial</p>
          </div>
        </div>
        <button
          onClick={onReiniciar}
          className="text-xs text-slate-400 hover:text-white flex items-center gap-1 cursor-pointer"
          title="Recargar los datos del entorno de pruebas"
        >
          <RotateCcw className="w-3.5 h-3.5" /> Reiniciar sandbox
        </button>
      </div>

      <nav className="max-w-7xl mx-auto px-3 sm:px-4 flex gap-1 overflow-x-auto">
        {MODULOS.map((m, i) => (
          <button
            key={m.id}
            onClick={() => onCambiar(m.id)}
            className={`flex items-center gap-2 px-3 py-2.5 text-xs sm:text-sm font-semibold border-b-2 whitespace-nowrap cursor-pointer transition ${
              activo === m.id
                ? 'border-indigo-400 text-white'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span className="text-slate-500 font-mono text-[11px]">{i + 1}</span>
            {m.icono}
            {m.nombre}
            {contadores[m.id] ? (
              <span className="text-[10px] bg-slate-800 text-slate-200 px-1.5 rounded-full">{contadores[m.id]}</span>
            ) : null}
          </button>
        ))}
      </nav>
    </header>
  );
};
