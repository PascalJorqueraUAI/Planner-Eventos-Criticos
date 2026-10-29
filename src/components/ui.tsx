import React from 'react';
import { AlertTriangle, CheckCircle2, Clock } from 'lucide-react';
import type { PartidaRiesgo, Prioridad } from '../domain/types.js';

export const clp = (n: number) => `$${Math.round(n).toLocaleString('es-CL')}`;

/** Desglose del riesgo estimado de un evento: qué costas asumiría Cobgestion si el apremio sigue. */
export const DesgloseRiesgo: React.FC<{ partidas?: PartidaRiesgo[] }> = ({ partidas }) =>
  partidas?.length ? (
    <p className="text-red-300/80">
      Riesgo estimado: {partidas.map((p) => `${p.concepto} ${clp(p.monto)}`).join(' · ')}
    </p>
  ) : null;

export const fecha = (iso: string | null | undefined) =>
  iso
    ? new Date(iso).toLocaleString('es-CL', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : '—';

/** "en 3 h" / "hace 2 h" respecto de `ahora` (la hora del motor, no la del navegador). */
export function relativo(iso: string, ahora: string) {
  const min = Math.round((new Date(iso).getTime() - new Date(ahora).getTime()) / 60000);
  const abs = Math.abs(min);
  if (abs < 1) return 'recién';
  const texto = abs < 60 ? `${abs} min` : abs < 48 * 60 ? `${Math.round(abs / 60)} h` : `${Math.round(abs / 1440)} d`;
  return min >= 0 ? `en ${texto}` : `hace ${texto}`;
}

export const Tarjeta: React.FC<{ className?: string; children: React.ReactNode }> = ({ className = '', children }) => (
  <section className={`min-w-0 bg-slate-900/80 border border-slate-800 rounded-2xl ${className}`}>{children}</section>
);

export const TituloSeccion: React.FC<{ icono: React.ReactNode; titulo: string; subtitulo?: string; acciones?: React.ReactNode }> = ({
  icono,
  titulo,
  subtitulo,
  acciones,
}) => (
  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 border-b border-slate-800">
    <div className="flex items-start gap-3">
      <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300">{icono}</div>
      <div>
        <h2 className="text-base font-bold text-white">{titulo}</h2>
        {subtitulo && <p className="text-xs text-slate-400 mt-0.5">{subtitulo}</p>}
      </div>
    </div>
    {acciones && <div className="flex flex-wrap gap-2">{acciones}</div>}
  </div>
);

const ESTILO_PRIORIDAD: Record<Prioridad, string> = {
  CRITICA: 'bg-red-500/15 text-red-300 border-red-500/40',
  ALTA: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  MEDIA: 'bg-sky-500/15 text-sky-300 border-sky-500/40',
};

export const BadgePrioridad: React.FC<{ prioridad: Prioridad }> = ({ prioridad }) => (
  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${ESTILO_PRIORIDAD[prioridad]}`}>
    {prioridad === 'CRITICA' ? 'CRÍTICA' : prioridad}
  </span>
);

export const BadgeEstadoTarea: React.FC<{ estado: string; vencida?: boolean }> = ({ estado, vencida }) => {
  if (estado === 'Atendida')
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded border bg-emerald-500/15 text-emerald-300 border-emerald-500/40">
        <CheckCircle2 className="w-3 h-3" /> Atendida
      </span>
    );
  if (vencida)
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded border bg-red-500/15 text-red-300 border-red-500/40">
        <AlertTriangle className="w-3 h-3" /> Vencida
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded border bg-amber-500/15 text-amber-300 border-amber-500/40">
      <Clock className="w-3 h-3" /> Pendiente
    </span>
  );
};

export const Etiqueta: React.FC<{ children: React.ReactNode; tono?: string }> = ({ children, tono = 'slate' }) => {
  const tonos: Record<string, string> = {
    slate: 'bg-slate-800 text-slate-300 border-slate-700',
    indigo: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
    emerald: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    amber: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    red: 'bg-red-500/15 text-red-300 border-red-500/30',
  };
  return <span className={`whitespace-nowrap text-[10px] font-semibold px-1.5 py-0.5 rounded border ${tonos[tono]}`}>{children}</span>;
};

export const tonoEstadoPago = (estado: string) =>
  estado === 'confirmado' ? 'emerald' : estado === 'observado' ? 'red' : 'amber';

export const Boton: React.FC<
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variante?: 'primario' | 'secundario' | 'peligro' }
> = ({ variante = 'secundario', className = '', ...props }) => {
  const estilos = {
    primario: 'bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-500',
    secundario: 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700',
    peligro: 'bg-red-600/90 hover:bg-red-500 text-white border-red-500',
  };
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-lg border transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${estilos[variante]} ${className}`}
    />
  );
};

export const campoBase =
  'bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500';

export const campo = `w-full ${campoBase}`;
