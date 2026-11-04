import React from 'react';
import { Mail, X, Info } from 'lucide-react';
import type { Correo } from '../domain/types.js';
import { fecha } from './ui.js';

interface Props {
  correos: Correo[];
  seleccionado: string | null;
  todos: boolean;
  onSeleccionar: (id: string) => void;
  onCerrar: () => void;
}

/**
 * Bandeja de correos simulados: lo que el sistema enviaría a las casillas @cobgestion.cl.
 * Cada correo tiene su propio enlace (#correos/MAIL-0001) para compartirlo o revisarlo después.
 */
export const BandejaCorreos: React.FC<Props> = ({ correos, seleccionado, todos, onSeleccionar, onCerrar }) => {
  const correo = correos.find((c) => c.id === seleccionado) ?? correos[0];
  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-start sm:items-center justify-center p-3 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-5xl w-full p-5 shadow-2xl text-xs">
        <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Mail className="w-5 h-5 text-indigo-300" /> Bandeja de correos {todos ? '(todos los usuarios)' : '(tus correos)'}
            </h2>
            <p className="text-slate-400 flex items-start gap-1.5 mt-0.5">
              <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              Envío simulado: estos correos van dirigidos a las casillas @cobgestion.cl, pero no salen del sistema. Así se revisan
              sin llenar ninguna casilla real.
            </p>
          </div>
          <button onClick={onCerrar} className="p-1 text-slate-400 hover:text-white cursor-pointer" aria-label="Cerrar">
            <X className="w-5 h-5" />
          </button>
        </div>

        {correos.length === 0 ? (
          <p className="py-8 text-center text-slate-500">
            Aún no hay correos. Se generan cuando el sistema asigna una tarea o un caso (por ejemplo, al crear un caso nuevo).
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mt-4">
            <ul className="md:col-span-2 max-h-[60vh] overflow-y-auto space-y-1.5">
              {correos.map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => onSeleccionar(c.id)}
                    className={`w-full text-left rounded-lg border px-2.5 py-2 cursor-pointer ${
                      c.id === correo?.id ? 'border-indigo-500/60 bg-indigo-500/10' : 'border-slate-800 bg-slate-950/60 hover:bg-slate-900'
                    }`}
                  >
                    <p className={`font-semibold truncate ${c.asunto.startsWith('[CRÍTICA]') ? 'text-red-300' : 'text-slate-100'}`}>
                      {c.asunto}
                    </p>
                    <p className="text-slate-500 truncate">
                      {c.para} · {fecha(c.fecha)}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
            {correo && (
              <article className="md:col-span-3 rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3">
                <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-slate-400">
                  <dt>De</dt>
                  <dd className="text-slate-200">notificaciones@cobgestion.cl</dd>
                  <dt>Para</dt>
                  <dd className="text-slate-200 break-all">
                    {correo.para_nombre} &lt;{correo.para}&gt;
                  </dd>
                  <dt>Fecha</dt>
                  <dd className="text-slate-200">{fecha(correo.fecha)}</dd>
                  <dt>Asunto</dt>
                  <dd className="text-white font-semibold">{correo.asunto}</dd>
                  <dt>Estado</dt>
                  <dd className="text-amber-300">{correo.estado === 'simulado' ? 'Simulado (no enviado)' : 'Enviado'}</dd>
                </dl>
                <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-slate-200 border-t border-slate-800 pt-3">
                  {correo.cuerpo}
                </pre>
                <p className="text-slate-500 break-all">
                  Enlace a este correo:{' '}
                  <a href={`#correos/${correo.id}`} className="text-indigo-300 hover:text-indigo-200">
                    {`${window.location.origin}/#correos/${correo.id}`}
                  </a>
                </p>
              </article>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
