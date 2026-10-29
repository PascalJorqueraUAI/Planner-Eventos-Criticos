import React, { useMemo, useState } from 'react';
import { Radar, BookOpen, Play, Lock } from 'lucide-react';
import { api, type Ejecutar } from '../api.js';
import type { EstadoSistema } from '../domain/types.js';
import { BadgeEstadoTarea, BadgePrioridad, Boton, DesgloseRiesgo, Etiqueta, Tarjeta, TituloSeccion, clp, fecha, relativo } from './ui.js';

interface Props {
  estado: EstadoSistema;
  ejecutar: Ejecutar;
  irATareas: () => void;
}

export const DetectorView: React.FC<Props> = ({ estado, ejecutar, irATareas }) => {
  const [soloAbiertos, setSoloAbiertos] = useState(true);
  const nombre = useMemo(
    () => Object.fromEntries(estado.colaboradores.map((c) => [c.id, c.nombre])),
    [estado.colaboradores],
  );
  const casos = useMemo(() => Object.fromEntries(estado.casos.map((c) => [c.id, c])), [estado.casos]);

  const orden = { CRITICA: 0, ALTA: 1, MEDIA: 2 };
  const eventos = estado.eventos
    .filter((e) => !soloAbiertos || e.estado === 'Abierto')
    .sort((a, b) => (a.estado === b.estado ? orden[a.prioridad] - orden[b.prioridad] : a.estado === 'Abierto' ? -1 : 1));

  return (
    <div className="space-y-5">
      <Tarjeta>
        <TituloSeccion
          icono={<Radar className="w-5 h-5" />}
          titulo="2 · Detector de eventos críticos"
          subtitulo={`Compara el estado de cada caso contra el catálogo cada minuto y después de cada cambio. Último escaneo: ${
            estado.ultimo_escaneo ? relativo(estado.ultimo_escaneo, estado.ahora) : '—'
          }.`}
          acciones={
            <Boton variante="primario" onClick={() => ejecutar(() => api.escanear(), 'Escaneo completado')}>
              <Play className="w-4 h-4" /> Escanear ahora
            </Boton>
          }
        />
        <div className="px-4 pt-3 flex items-center gap-3 text-xs">
          <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
            <input type="checkbox" checked={soloAbiertos} onChange={(e) => setSoloAbiertos(e.target.checked)} />
            Solo eventos abiertos
          </label>
          <span className="text-slate-500">
            {estado.metricas.eventos_abiertos} abiertos · {estado.metricas.eventos_cerrados} cerrados
          </span>
        </div>
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          {eventos.length === 0 && <p className="text-xs text-slate-500">No hay eventos para mostrar.</p>}
          {eventos.map((e) => {
            const caso = casos[e.caso_id];
            const tareas = estado.tareas.filter((t) => t.evento_id === e.id);
            const pendientes = tareas.filter((t) => t.estado === 'Pendiente');
            return (
              <article
                key={e.id}
                className={`rounded-xl border p-3 text-xs space-y-2 ${
                  e.estado === 'Cerrado'
                    ? 'border-slate-800 bg-slate-950/40 opacity-75'
                    : e.prioridad === 'CRITICA'
                      ? 'border-red-500/40 bg-red-950/20'
                      : 'border-slate-700 bg-slate-950/60'
                }`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Etiqueta tono="indigo">{e.codigo}</Etiqueta>
                  <BadgePrioridad prioridad={e.prioridad} />
                  {e.estado === 'Cerrado' ? <Etiqueta tono="emerald">Cerrado</Etiqueta> : <Etiqueta tono="amber">Abierto</Etiqueta>}
                  <span className="ml-auto text-slate-500">{fecha(e.fecha_deteccion)}</span>
                </div>
                <p className="font-bold text-white text-sm">{e.nombre}</p>
                <p className="text-slate-300">
                  {caso.id} · {caso.deudor.nombre} · {caso.rol_causa}
                  {e.riesgo_clp > 0 && <span className="text-red-300"> · riesgo {clp(e.riesgo_clp)}</span>}
                </p>
                <p className="text-slate-500">{e.motivo}</p>
                <DesgloseRiesgo partidas={e.riesgo_detalle} />
                <ul className="space-y-1">
                  {tareas.map((t) => (
                    <li key={t.id} className="flex flex-wrap items-center gap-2 bg-slate-900/80 rounded-lg px-2 py-1.5">
                      <Etiqueta tono={t.area === 'Judicial' ? 'indigo' : 'emerald'}>{t.area}</Etiqueta>
                      <span className="text-slate-300">{nombre[t.responsable_id ?? ''] ?? 'Sin asignar'}</span>
                      <span className="ml-auto">
                        <BadgeEstadoTarea estado={t.estado} vencida={t.vencida} />
                      </span>
                    </li>
                  ))}
                </ul>
                {e.estado === 'Abierto' && pendientes.length > 0 && pendientes.length < tareas.length && (
                  <p className="flex items-center gap-1.5 text-amber-300">
                    <Lock className="w-3.5 h-3.5" /> Cierre bloqueado hasta que {pendientes.map((t) => t.area).join(' y ')} atienda su tarea.
                  </p>
                )}
                {e.estado === 'Abierto' && (
                  <button onClick={irATareas} className="text-indigo-300 hover:text-indigo-200 cursor-pointer">
                    Gestionar tareas →
                  </button>
                )}
              </article>
            );
          })}
        </div>
      </Tarjeta>

      <Tarjeta>
        <TituloSeccion
          icono={<BookOpen className="w-5 h-5" />}
          titulo="Catálogo de eventos críticos"
          subtitulo="Una causa con apremio en curso (embargo, incautación o receptor programado) eleva cualquier evento a CRÍTICO y acorta su SLA."
        />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-xs">
            <thead className="text-left text-slate-500 border-b border-slate-800">
              <tr>
                <th className="px-4 py-2 font-medium">Código</th>
                <th className="px-2 font-medium">Evento y condición</th>
                <th className="px-2 font-medium">Tareas paralelas (SLA normal / crítico)</th>
                <th className="px-4 font-medium text-right">Detectados</th>
              </tr>
            </thead>
            <tbody>
              {estado.catalogo.map((r) => (
                <tr key={r.codigo} className="border-b border-slate-800/70 align-top">
                  <td className="px-4 py-3">
                    <Etiqueta tono="indigo">{r.codigo}</Etiqueta>
                  </td>
                  <td className="px-2 py-3">
                    <p className="font-semibold text-white">{r.nombre}</p>
                    <p className="text-slate-400 mt-0.5">{r.descripcion}</p>
                    <p className="text-slate-500 mt-1 font-mono text-[11px]">SI {r.condicion}</p>
                  </td>
                  <td className="px-2 py-3 space-y-1">
                    {r.tareas.map((t) => (
                      <p key={t.tipo} className="text-slate-300">
                        <Etiqueta tono={t.area === 'Judicial' ? 'indigo' : 'emerald'}>{t.area}</Etiqueta> {t.titulo}{' '}
                        <span className="text-slate-500">
                          ({t.sla_horas} h / {t.sla_horas_critica} h)
                        </span>
                      </p>
                    ))}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-200 font-semibold">{estado.metricas.eventos_por_codigo[r.codigo] ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Tarjeta>
    </div>
  );
};
