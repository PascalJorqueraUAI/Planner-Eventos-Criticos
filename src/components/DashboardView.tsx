import React, { useState } from 'react';
import { BarChart3, ListChecks, AlertTriangle, ShieldCheck } from 'lucide-react';
import type { EstadoSistema } from '../domain/types.js';
import { Etiqueta, Tarjeta, TituloSeccion, campoBase, clp, fecha } from './ui.js';

export const DashboardView: React.FC<{ estado: EstadoSistema }> = ({ estado }) => {
  const m = estado.metricas;
  const [areaLog, setAreaLog] = useState('Todas');
  const nombresEvento = Object.fromEntries(estado.catalogo.map((r) => [r.codigo, `${r.codigo} · ${r.nombre}`]));
  const log = estado.historial.filter((h) => areaLog === 'Todas' || h.area === areaLog);

  return (
    <div className="space-y-5">
      <Tarjeta>
        <TituloSeccion
          icono={<BarChart3 className="w-5 h-5" />}
          titulo="4 · Dashboard de trazabilidad"
          subtitulo="Estado real de los casos y desempeño de la coordinación, calculado en el momento desde el repositorio (se actualiza cada 15 s)."
        />
        <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          <Indicador titulo="Casos en el repositorio" valor={m.total_casos} />
          <Indicador
            titulo="Eventos abiertos"
            valor={m.eventos_abiertos}
            detalle={`${m.eventos_criticos_abiertos} críticos · ${m.eventos_cerrados} cerrados`}
            alerta={m.eventos_criticos_abiertos > 0}
          />
          <Indicador
            titulo="Tareas pendientes"
            valor={m.tareas_pendientes}
            detalle={`${m.tareas_vencidas} vencidas · ${m.tareas_escaladas} escaladas`}
            alerta={m.tareas_vencidas > 0}
          />
          <Indicador
            titulo="Cumplimiento de SLA"
            valor={m.cumplimiento_sla_pct == null ? '—' : `${m.cumplimiento_sla_pct}%`}
            detalle={`${m.tareas_atendidas} tareas atendidas`}
          />
          <Indicador
            titulo="Desfase aviso → alerta judicial"
            valor={m.minutos_promedio_aviso_a_alerta == null ? '—' : `${m.minutos_promedio_aviso_a_alerta} min`}
            detalle="Caso del auto: ~4 días"
          />
          <Indicador
            titulo="Tiempo medio de atención"
            valor={m.horas_promedio_atencion == null ? '—' : `${m.horas_promedio_atencion} h`}
            detalle="desde la detección"
          />
          <Indicador titulo="Riesgo expuesto" valor={clp(m.riesgo_expuesto_clp)} detalle="costas en eventos abiertos" alerta={m.riesgo_expuesto_clp > 0} />
          <Indicador titulo="Riesgo cubierto" valor={clp(m.riesgo_cubierto_clp)} detalle="Judicial actuó dentro del SLA" />
        </div>
      </Tarjeta>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Tarjeta className="p-4">
          <Barras titulo="Casos por estado judicial" datos={m.casos_por_estado_judicial} unidad="casos" />
        </Tarjeta>
        <Tarjeta className="p-4">
          <Barras titulo="Casos por estado comercial" datos={m.casos_por_estado_comercial} unidad="casos" />
        </Tarjeta>
        <Tarjeta className="p-4">
          <Barras
            titulo="Eventos detectados por tipo"
            datos={Object.fromEntries(Object.entries(m.eventos_por_codigo).map(([k, v]) => [nombresEvento[k] ?? k, v]))}
            unidad="eventos"
          />
        </Tarjeta>
        <Tarjeta className="p-4">
          <h3 className="text-sm font-semibold text-white mb-3">Carga y desempeño por colaborador</h3>
          <table className="w-full text-xs">
            <thead className="text-slate-500 text-left">
              <tr>
                <th className="font-medium pb-1.5">Colaborador</th>
                <th className="font-medium pb-1.5">Carga</th>
                <th className="font-medium pb-1.5 text-right">Pend.</th>
                <th className="font-medium pb-1.5 text-right">Vencidas</th>
                <th className="font-medium pb-1.5 text-right">SLA hist.</th>
              </tr>
            </thead>
            <tbody>
              {m.colaboradores.map((c) => (
                <tr key={c.id} className="border-t border-slate-800">
                  <td className="py-1.5">
                    <p className={c.disponible ? 'text-slate-200' : 'text-slate-500 line-through'}>{c.nombre}</p>
                    <p className="text-slate-600">{c.cargo}</p>
                  </td>
                  <td>
                    <span className="flex items-center gap-1.5" title={`${c.carga} de ${c.capacidad}`}>
                      <span className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                        <span className="block h-full rounded-full bg-indigo-400" style={{ width: `${Math.min(100, (100 * c.carga) / c.capacidad)}%` }} />
                      </span>
                      <span className="tabular-nums text-slate-400">
                        {c.carga}/{c.capacidad}
                      </span>
                    </span>
                  </td>
                  <td className="text-right tabular-nums text-slate-300">{c.pendientes}</td>
                  <td className="text-right tabular-nums">
                    {c.vencidas > 0 ? (
                      <span className="inline-flex items-center gap-1 text-red-300">
                        <AlertTriangle className="w-3 h-3" /> {c.vencidas}
                      </span>
                    ) : (
                      <span className="text-slate-500">0</span>
                    )}
                  </td>
                  <td className="text-right tabular-nums text-slate-300">
                    {c.historico.tasa_sla == null ? '—' : `${Math.round(c.historico.tasa_sla * 100)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Tarjeta>
      </div>

      <Tarjeta>
        <TituloSeccion
          icono={<ListChecks className="w-5 h-5" />}
          titulo="Registro de auditoría"
          subtitulo="Cada decisión queda registrada: quién, cuándo, qué área y qué cambió."
          acciones={
            <select value={areaLog} onChange={(e) => setAreaLog(e.target.value)} className={campoBase} aria-label="Filtrar área">
              {['Todas', 'Comercial', 'Judicial', 'Sistema', 'Integración', 'Protección de datos'].map((a) => (
                <option key={a}>{a}</option>
              ))}
            </select>
          }
        />
        <div className="overflow-x-auto max-h-[460px] overflow-y-auto">
          <table className="w-full min-w-[760px] text-xs">
            <thead className="text-slate-500 text-left sticky top-0 bg-slate-900">
              <tr>
                <th className="px-4 py-2 font-medium">Fecha</th>
                <th className="px-2 font-medium">Área</th>
                <th className="px-2 font-medium">Usuario</th>
                <th className="px-2 font-medium">Acción</th>
                <th className="px-4 font-medium">Detalle</th>
              </tr>
            </thead>
            <tbody>
              {log.map((h) => (
                <tr key={h.id} className="border-t border-slate-800/70 align-top">
                  <td className="px-4 py-1.5 font-mono text-slate-500 whitespace-nowrap">{fecha(h.timestamp)}</td>
                  <td className="px-2">
                    <Etiqueta tono={h.area === 'Judicial' ? 'indigo' : h.area === 'Comercial' ? 'emerald' : 'slate'}>{h.area}</Etiqueta>
                  </td>
                  <td className="px-2 text-slate-400">{h.usuario}</td>
                  <td className="px-2 text-slate-200">{h.accion}</td>
                  <td className="px-4 text-slate-400">
                    {h.caso_id && <span className="text-slate-500">{h.caso_id} · </span>}
                    {h.detalle}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Tarjeta>

      <Tarjeta>
        <TituloSeccion
          icono={<ShieldCheck className="w-5 h-5" />}
          titulo="Registro de tratamientos con terceros"
          subtitulo={`Cada envío de datos a un encargado del tratamiento (Gemini), con su finalidad y resguardos. Nunca se guarda el contenido, solo su huella SHA-256. ${estado.extraccion.motivo}`}
        />
        {estado.tratamientos.length === 0 ? (
          <p className="p-4 text-xs text-slate-500">No se han enviado datos a terceros.</p>
        ) : (
          <div className="overflow-x-auto max-h-[360px] overflow-y-auto">
            <table className="w-full min-w-[820px] text-xs">
              <thead className="text-slate-500 text-left sticky top-0 bg-slate-900">
                <tr>
                  <th className="px-4 py-2 font-medium">Fecha</th>
                  <th className="px-2 font-medium">Operador</th>
                  <th className="px-2 font-medium">Entrada</th>
                  <th className="px-2 font-medium">Destino</th>
                  <th className="px-2 font-medium">Medidas aplicadas</th>
                  <th className="px-2 font-medium">Huella</th>
                  <th className="px-4 font-medium">Resultado</th>
                </tr>
              </thead>
              <tbody>
                {estado.tratamientos.map((t) => (
                  <tr key={t.id} className="border-t border-slate-800/70 align-top">
                    <td className="px-4 py-1.5 font-mono text-slate-500 whitespace-nowrap">{fecha(t.timestamp)}</td>
                    <td className="px-2 text-slate-300">{t.usuario}</td>
                    <td className="px-2 text-slate-300">{t.tipo_entrada}</td>
                    <td className="px-2 text-slate-400">
                      {t.modelo}
                      <p className="text-slate-600">{t.ubicacion}</p>
                    </td>
                    <td className="px-2 text-slate-400">{t.medidas.join(' · ')}</td>
                    <td className="px-2 font-mono text-slate-500" title={t.hash_entrada}>
                      {t.hash_entrada.slice(0, 10)}…
                    </td>
                    <td className="px-4">
                      <Etiqueta tono={t.resultado === 'ok' ? 'emerald' : 'red'}>{t.resultado}</Etiqueta>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Tarjeta>
    </div>
  );
};

const Indicador: React.FC<{ titulo: string; valor: React.ReactNode; detalle?: string; alerta?: boolean }> = ({
  titulo,
  valor,
  detalle,
  alerta,
}) => (
  <div className={`rounded-xl border p-3 ${alerta ? 'border-red-500/40 bg-red-950/20' : 'border-slate-800 bg-slate-950/50'}`}>
    <p className="text-[11px] text-slate-400 flex items-center gap-1">
      {alerta && <AlertTriangle className="w-3 h-3 text-red-400" />} {titulo}
    </p>
    <p className="text-xl font-bold text-white mt-1 tabular-nums">{valor}</p>
    {detalle && <p className="text-[11px] text-slate-500 mt-0.5">{detalle}</p>}
  </div>
);

/** Barras horizontales de una sola serie: magnitud en un solo tono, valor rotulado al final de cada barra. */
const Barras: React.FC<{ titulo: string; datos: Record<string, number>; unidad: string }> = ({ titulo, datos, unidad }) => {
  const filas = Object.entries(datos).sort((a, b) => b[1] - a[1]);
  const maximo = Math.max(1, ...filas.map(([, v]) => v));
  return (
    <div>
      <h3 className="text-sm font-semibold text-white mb-3">{titulo}</h3>
      {filas.length === 0 && <p className="text-xs text-slate-500">Sin datos.</p>}
      <ul className="space-y-2">
        {filas.map(([etiqueta, valor]) => (
          <li key={etiqueta} className="text-xs group" title={`${etiqueta}: ${valor} ${unidad}`}>
            <p className="text-slate-400 mb-0.5 truncate">{etiqueta}</p>
            <div className="flex items-center gap-2">
              <span className="flex-1 h-2.5">
                <span
                  className="block h-full rounded-r bg-indigo-400 group-hover:bg-indigo-300 transition-colors"
                  style={{ width: `${(100 * valor) / maximo}%` }}
                />
              </span>
              <span className="w-6 text-right tabular-nums text-slate-200">{valor}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};
