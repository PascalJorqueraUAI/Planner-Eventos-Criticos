import React, { useEffect, useRef, useState } from 'react';
import { Bell, Mail, CheckCheck } from 'lucide-react';
import type { Notificacion } from '../domain/types.js';
import { relativo } from './ui.js';

const TONO: Record<Notificacion['tipo'], string> = {
  asignacion: 'text-indigo-300',
  reasignacion: 'text-indigo-300',
  escalamiento: 'text-red-300',
  vencida: 'text-amber-300',
  tarea_retirada: 'text-slate-400',
  titular: 'text-emerald-300',
};

interface Props {
  notificaciones: Notificacion[];
  sinLeer: number;
  ahora: string;
  onLeer: (ids?: string[]) => void;
  onVerCorreo: (correoId: string) => void;
  onIrATarea: () => void;
}

export const CampanaNotificaciones: React.FC<Props> = ({ notificaciones, sinLeer, ahora, onLeer, onVerCorreo, onIrATarea }) => {
  const [abierto, setAbierto] = useState(false);
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!abierto) return;
    const cerrar = (e: MouseEvent) => {
      if (panel.current && !panel.current.contains(e.target as Node)) setAbierto(false);
    };
    document.addEventListener('mousedown', cerrar);
    return () => document.removeEventListener('mousedown', cerrar);
  }, [abierto]);

  const abrir = (n: Notificacion, accion: () => void) => {
    if (!n.leida) onLeer([n.id]);
    setAbierto(false);
    accion();
  };

  return (
    <div className="relative" ref={panel}>
      <button
        onClick={() => setAbierto((v) => !v)}
        className="relative p-1.5 rounded-lg hover:bg-slate-800 text-slate-300 cursor-pointer"
        aria-label={`Notificaciones (${sinLeer} sin leer)`}
      >
        <Bell className="w-4.5 h-4.5" />
        {sinLeer > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-4 h-4 px-1 rounded-full bg-red-600 text-white text-[10px] font-bold flex items-center justify-center">
            {sinLeer > 9 ? '9+' : sinLeer}
          </span>
        )}
      </button>
      {abierto && (
        <div className="absolute right-0 mt-2 w-[min(22rem,calc(100vw-2rem))] bg-slate-900 border border-slate-700 rounded-xl shadow-2xl z-50 text-xs">
          <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800">
            <p className="font-semibold text-white">Notificaciones</p>
            {sinLeer > 0 && (
              <button onClick={() => onLeer()} className="flex items-center gap-1 text-indigo-300 hover:text-indigo-200 cursor-pointer">
                <CheckCheck className="w-3.5 h-3.5" /> Marcar todas como leídas
              </button>
            )}
          </div>
          <ul className="max-h-96 overflow-y-auto divide-y divide-slate-800">
            {notificaciones.length === 0 && <li className="px-3 py-4 text-slate-500">Sin notificaciones.</li>}
            {notificaciones.map((n) => (
              <li key={n.id} className={`px-3 py-2.5 space-y-1 ${n.leida ? 'opacity-60' : 'bg-indigo-500/5'}`}>
                <div className="flex items-center gap-2">
                  {!n.leida && <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />}
                  <span className={`font-semibold ${TONO[n.tipo]}`}>{n.titulo}</span>
                  {n.prioridad === 'CRITICA' && <span className="text-[10px] font-bold text-red-300">CRÍTICA</span>}
                  <span className="ml-auto text-slate-500 whitespace-nowrap">{relativo(n.fecha, ahora)}</span>
                </div>
                <p className="text-slate-300">{n.mensaje}</p>
                <div className="flex gap-3">
                  {n.tarea_id && n.tipo !== 'tarea_retirada' && (
                    <button onClick={() => abrir(n, onIrATarea)} className="text-indigo-300 hover:text-indigo-200 cursor-pointer">
                      Ver tareas →
                    </button>
                  )}
                  {n.correo_id && (
                    <button
                      onClick={() => abrir(n, () => onVerCorreo(n.correo_id!))}
                      className="flex items-center gap-1 text-slate-400 hover:text-slate-200 cursor-pointer"
                    >
                      <Mail className="w-3.5 h-3.5" /> Ver correo
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
