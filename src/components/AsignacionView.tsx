import React, { useMemo, useState } from 'react';
import { Users, Grid3x3, ChevronDown, ChevronUp, Shuffle, CheckCircle2, UserX, UserCheck, AlertTriangle, CalendarOff } from 'lucide-react';
import { api, type Ejecutar } from '../api.js';
import type { Colaborador, EstadoSistema, Tarea } from '../domain/types.js';
import { BadgeEstadoTarea, BadgePrioridad, Boton, Etiqueta, Tarjeta, TituloSeccion, campo, campoBase, fecha, relativo } from './ui.js';

type Filtro = 'pendientes' | 'vencidas' | 'atendidas' | 'todas';

const CRITERIOS: { clave: 'experiencia' | 'desempeno' | 'disponibilidad' | 'continuidad'; nombre: string; ayuda: string }[] = [
  { clave: 'experiencia', nombre: 'Experiencia', ayuda: 'n / (n + 5), n = tareas de este tipo ya atendidas' },
  { clave: 'desempeno', nombre: 'Desempeño', ayuda: 'cumplidas en SLA + 1 / (n + 2)' },
  { clave: 'disponibilidad', nombre: 'Disponibilidad', ayuda: '1 − carga / capacidad' },
  { clave: 'continuidad', nombre: 'Continuidad', ayuda: '1 si es titular del caso' },
];

interface Props {
  estado: EstadoSistema;
  ejecutar: Ejecutar;
}

export const AsignacionView: React.FC<Props> = ({ estado, ejecutar }) => {
  const [filtro, setFiltro] = useState<Filtro>('pendientes');
  const [area, setArea] = useState<'todas' | 'Comercial' | 'Judicial'>('todas');

  const colaboradores = useMemo(() => Object.fromEntries(estado.colaboradores.map((c) => [c.id, c])), [estado.colaboradores]);
  const resultados = useMemo(
    () => Object.fromEntries(estado.catalogo.flatMap((r) => r.tareas.map((t) => [t.tipo, t.resultados]))),
    [estado.catalogo],
  );
  const titulos = useMemo(
    () => Object.fromEntries(estado.catalogo.flatMap((r) => r.tareas.map((t) => [t.tipo, t.titulo]))),
    [estado.catalogo],
  );

  const orden = { CRITICA: 0, ALTA: 1, MEDIA: 2 };
  const tareas = estado.tareas
    .filter((t) =>
      filtro === 'pendientes' ? t.estado === 'Pendiente' : filtro === 'vencidas' ? t.vencida : filtro === 'atendidas' ? t.estado === 'Atendida' : true,
    )
    .filter((t) => area === 'todas' || t.area === area)
    .sort((a, b) => orden[a.prioridad] - orden[b.prioridad] || a.fecha_limite.localeCompare(b.fecha_limite));

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <Tarjeta className="xl:col-span-2">
          <TituloSeccion
            icono={<Users className="w-5 h-5" />}
            titulo="3 · Asignación y seguimiento"
            subtitulo="Cada tarea se asigna automáticamente al colaborador más adecuado y queda Pendiente hasta que se marque como Atendida."
          />
          <div className="mx-4 mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
            <div className="rounded-lg border border-emerald-500/25 bg-emerald-500/5 p-2.5 text-slate-300">
              <p className="font-semibold text-emerald-300 mb-1">Automático (cada minuto, sin intervención)</p>
              <ul className="space-y-0.5 list-disc pl-4">
                <li>Asignar cada tarea nueva (RACI + método húngaro)</li>
                <li>Aplicar el calendario de ausencias y reasignar lo pendiente</li>
                <li>No asignar a quien se ausenta antes del vencimiento</li>
                <li>Tarea vencida → otro colaborador; si vuelve a vencer → jefatura</li>
              </ul>
            </div>
            <div className="rounded-lg border border-slate-700 bg-slate-950/50 p-2.5 text-slate-300">
              <p className="font-semibold text-slate-200 mb-1">Manual</p>
              <ul className="space-y-0.5 list-disc pl-4">
                <li>Marcar la tarea como atendida con su resultado</li>
                <li>Excepciones: reasignar a pedido o marcar una ausencia imprevista</li>
              </ul>
              <p className="text-slate-500 mt-1">
                {estado.metricas.tareas_escaladas_por_vencimiento} tarea(s) escalada(s) por vencimiento hasta ahora.
              </p>
            </div>
          </div>
          <div className="px-4 pt-3 flex flex-wrap gap-2 text-xs">
            {(['pendientes', 'vencidas', 'atendidas', 'todas'] as Filtro[]).map((f) => (
              <button
                key={f}
                onClick={() => setFiltro(f)}
                className={`px-2.5 py-1 rounded-lg border capitalize cursor-pointer ${
                  filtro === f ? 'bg-indigo-600/25 border-indigo-500 text-white' : 'border-slate-700 text-slate-400'
                }`}
              >
                {f}
              </button>
            ))}
            <select value={area} onChange={(e) => setArea(e.target.value as any)} className={`${campoBase} ml-auto`} aria-label="Área">
              <option value="todas">Ambas áreas</option>
              <option>Comercial</option>
              <option>Judicial</option>
            </select>
          </div>
          <div className="p-4 space-y-3">
            {tareas.length === 0 && <p className="text-xs text-slate-500">No hay tareas en este filtro.</p>}
            {tareas.map((t) => (
              <TarjetaTarea
                key={t.id}
                tarea={t}
                estado={estado}
                colaboradores={colaboradores}
                resultados={resultados[t.tipo] ?? []}
                ejecutar={ejecutar}
              />
            ))}
          </div>
        </Tarjeta>

        <PanelColaboradores estado={estado} ejecutar={ejecutar} />
      </div>

      <Tarjeta>
        <TituloSeccion
          icono={<Grid3x3 className="w-5 h-5" />}
          titulo="Matriz RACI por tipo de tarea"
          subtitulo="R ejecuta (el modelo elige a la persona entre quienes tienen ese cargo) · A aprueba y recibe escalamientos · C se consulta · I se informa."
        />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-xs">
            <thead className="text-slate-500 border-b border-slate-800">
              <tr>
                <th className="px-4 py-2 text-left font-medium">Tarea</th>
                {Object.keys(Object.values(estado.matriz_raci)[0] ?? {}).map((cargo) => (
                  <th key={cargo} className="px-2 font-medium">
                    {cargo}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(estado.matriz_raci).map(([tipo, fila]) => (
                <tr key={tipo} className="border-b border-slate-800/70">
                  <td className="px-4 py-2 text-slate-300">{titulos[tipo] ?? tipo}</td>
                  {Object.entries(fila).map(([cargo, letra]) => (
                    <td key={cargo} className="px-2 text-center">
                      <span
                        className={`inline-block w-6 py-0.5 rounded font-bold ${
                          letra === 'R'
                            ? 'bg-indigo-500 text-white'
                            : letra === 'A'
                              ? 'bg-indigo-500/30 text-indigo-200'
                              : letra === '-'
                                ? 'text-slate-700'
                                : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {letra}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-4 text-xs text-slate-400 space-y-1 border-t border-slate-800">
          <p className="font-semibold text-slate-200">Modelo de asignación (investigación de operaciones)</p>
          <p>
            Problema de asignación: maximizar Σ puntaje(colaborador, tarea) sujeto a que cada tarea tenga un responsable, nadie
            supere su capacidad y solo participen colaboradores disponibles, con la competencia y el cargo R. Se resuelve con el{' '}
            <strong className="text-slate-200">método húngaro</strong> sobre todas las tareas nuevas a la vez; si no hay nadie
            factible, la tarea se escala a la jefatura (A).
          </p>
          <p>
            Pesos normales:{' '}
            {CRITERIOS.map((c) => `${c.nombre} ${Math.round(estado.pesos_asignacion.normal[c.clave] * 100)}%`).join(' · ')}. En tareas
            críticas:{' '}
            {CRITERIOS.map((c) => `${c.nombre} ${Math.round(estado.pesos_asignacion.CRITICA[c.clave] * 100)}%`).join(' · ')}.
          </p>
        </div>
      </Tarjeta>
    </div>
  );
};

const TarjetaTarea: React.FC<{
  tarea: Tarea;
  estado: EstadoSistema;
  colaboradores: Record<string, Colaborador>;
  resultados: string[];
  ejecutar: Ejecutar;
}> = ({ tarea, estado, colaboradores, resultados, ejecutar }) => {
  const [detalle, setDetalle] = useState(false);
  const [resultado, setResultado] = useState(resultados[0] ?? '');
  const [notas, setNotas] = useState('');
  const caso = estado.casos.find((c) => c.id === tarea.caso_id)!;
  const responsable = tarea.responsable_id ? colaboradores[tarea.responsable_id] : null;
  const a = tarea.asignacion;

  const atender = () =>
    ejecutar(
      () => api.atenderTarea(tarea.id, resultado, notas, responsable?.nombre ?? 'Responsable'),
      `Tarea ${tarea.id} atendida`,
    );
  const reasignar = () => {
    const motivo = prompt('Motivo de la reasignación', 'Sobrecarga del responsable');
    if (motivo !== null) ejecutar(() => api.reasignarTarea(tarea.id, motivo), `Tarea ${tarea.id} reasignada`);
  };

  return (
    <article
      className={`rounded-xl border p-3 text-xs ${
        tarea.vencida ? 'border-red-500/50 bg-red-950/20' : tarea.estado === 'Atendida' ? 'border-slate-800 bg-slate-950/40' : 'border-slate-700 bg-slate-950/60'
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Etiqueta tono={tarea.area === 'Judicial' ? 'indigo' : 'emerald'}>{tarea.area}</Etiqueta>
        <BadgePrioridad prioridad={tarea.prioridad} />
        <BadgeEstadoTarea estado={tarea.estado} vencida={tarea.vencida} />
        {a.escalada && <Etiqueta tono="red">Escalada a jefatura</Etiqueta>}
        {tarea.nivel_escalamiento === 1 && <Etiqueta tono="amber">Reasignada por vencimiento</Etiqueta>}
        {tarea.reasignaciones > 0 && <Etiqueta>Reasignada ×{tarea.reasignaciones}</Etiqueta>}
        <span className="ml-auto text-slate-500 font-mono">{tarea.id}</span>
      </div>
      <p className="font-bold text-white text-sm mt-2">{tarea.titulo}</p>
      <p className="text-slate-400 mt-0.5">{tarea.descripcion}</p>
      <p className="text-slate-500 mt-1">
        {caso.id} · {caso.deudor.nombre} · SLA {tarea.sla_horas} h · vence {fecha(tarea.fecha_limite)}
        {tarea.estado === 'Pendiente' && ` (${relativo(tarea.fecha_limite, estado.ahora)})`}
      </p>
      {tarea.estado === 'Pendiente' && tarea.plazo_escalamiento && (
        <p className="text-amber-300 mt-0.5">
          Plazo del responsable actual: {fecha(tarea.plazo_escalamiento)} ({relativo(tarea.plazo_escalamiento, estado.ahora)})
          {tarea.nivel_escalamiento === 1 && ' · si vence, pasa a la jefatura'}
        </p>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="text-slate-300">
          Responsable: <strong className="text-white">{responsable?.nombre ?? 'Sin asignar'}</strong>
          {a.puntaje != null && <span className="text-slate-500"> · puntaje {a.puntaje.toFixed(2)}</span>}
        </span>
        {(['A', 'C', 'I'] as const).map((rol) =>
          tarea.raci[rol]?.length ? (
            <span key={rol} className="text-slate-500">
              <strong className="text-slate-300">{rol}:</strong> {tarea.raci[rol]!.map((id) => colaboradores[id]?.nombre ?? id).join(', ')}
            </span>
          ) : null,
        )}
        <button onClick={() => setDetalle((v) => !v)} className="text-indigo-300 hover:text-indigo-200 flex items-center gap-1 cursor-pointer">
          ¿Por qué esta persona? {detalle ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {detalle && (
        <div className="mt-2 bg-slate-900 border border-slate-800 rounded-lg p-3 space-y-3">
          <p className="text-slate-400">{a.metodo}</p>
          <table className="w-full">
            <thead className="text-slate-500 text-left">
              <tr>
                <th className="font-medium pb-1">Candidato</th>
                {CRITERIOS.map((c) => (
                  <th key={c.clave} className="font-medium pb-1" title={c.ayuda}>
                    {c.nombre}
                  </th>
                ))}
                <th className="font-medium pb-1 text-right">Puntaje</th>
              </tr>
            </thead>
            <tbody>
              {a.candidatos.map((c) => (
                <tr key={c.id} className={c.id === tarea.responsable_id ? 'text-white font-semibold' : 'text-slate-400'}>
                  <td className="py-0.5">{c.nombre}</td>
                  {CRITERIOS.map((k) => (
                    <td key={k.clave}>
                      <Medidor valor={c.criterios[k.clave]} />
                    </td>
                  ))}
                  <td className="text-right">{c.puntaje.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-slate-600">
            Puntaje según la carga al momento de evaluar; dentro de un lote el método húngaro reparte considerando la carga que
            agrega cada tarea.
          </p>
          {a.excluidos.length > 0 && (
            <ul className="space-y-0.5">
              {a.excluidos.map((x) => (
                <li key={x.id} className="text-slate-500 flex items-center gap-1.5">
                  <UserX className="w-3.5 h-3.5 text-red-400" /> {x.nombre}: {x.motivo}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {tarea.estado === 'Pendiente' ? (
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto_auto] gap-2">
          <select value={resultado} onChange={(e) => setResultado(e.target.value)} className={campo} aria-label="Resultado">
            {resultados.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
          <input value={notas} onChange={(e) => setNotas(e.target.value)} placeholder="Notas (opcional)" className={campo} />
          <Boton variante="primario" onClick={atender}>
            <CheckCircle2 className="w-4 h-4" /> Marcar atendida
          </Boton>
          <Boton onClick={reasignar}>
            <Shuffle className="w-4 h-4" /> Reasignar
          </Boton>
        </div>
      ) : (
        <p className="mt-2 text-emerald-300">
          Resultado: {tarea.resultado} · {fecha(tarea.fecha_atencion)} por {tarea.atendida_por}
          {tarea.notas && <span className="text-slate-400"> — {tarea.notas}</span>}
        </p>
      )}
    </article>
  );
};

const Medidor: React.FC<{ valor: number }> = ({ valor }) => (
  <span className="inline-flex items-center gap-1.5" title={valor.toFixed(2)}>
    <span className="w-12 h-1.5 rounded-full bg-slate-800 overflow-hidden">
      <span className="block h-full rounded-full bg-indigo-400" style={{ width: `${Math.round(valor * 100)}%` }} />
    </span>
    <span className="tabular-nums">{valor.toFixed(2)}</span>
  </span>
);

const PanelColaboradores: React.FC<{ estado: EstadoSistema; ejecutar: Ejecutar }> = ({ estado, ejecutar }) => (
  <Tarjeta>
    <TituloSeccion
      icono={<Users className="w-5 h-5" />}
      titulo="Colaboradores"
      subtitulo="Disponibilidad según el calendario de ausencias, carga actual (CRM + tareas del sistema) e historial usado por el modelo."
    />
    <ul className="p-4 space-y-3 text-xs">
      {estado.colaboradores.map((c) => (
        <FilaColaborador key={c.id} colaborador={c} ahora={estado.ahora} ejecutar={ejecutar} />
      ))}
    </ul>
  </Tarjeta>
);

const FilaColaborador: React.FC<{ colaborador: Colaborador; ahora: string; ejecutar: Ejecutar }> = ({ colaborador: c, ahora, ejecutar }) => {
  const [formulario, setFormulario] = useState(false);
  const [ausencia, setAusencia] = useState({ desde: ahora.slice(0, 16), hasta: '', motivo: 'Vacaciones' });
  const ocupacion = c.carga_actual / c.capacidad_max;
  const proximas = (c.ausencias ?? []).filter((a) => a.hasta > ahora);

  const alternar = () => {
    if (c.disponible) {
      const motivo = prompt(`¿Por qué ${c.nombre} no está disponible? Sus tareas pendientes se reasignarán.`, 'Ausencia imprevista');
      if (motivo === null) return;
      ejecutar(() => api.cambiarDisponibilidad(c.id, false, motivo), `${c.nombre} marcado como no disponible`);
    } else {
      ejecutar(() => api.cambiarDisponibilidad(c.id, true, ''), `${c.nombre} disponible nuevamente`);
    }
  };

  const programar = async () => {
    await ejecutar(
      () => api.registrarAusencia(c.id, `${ausencia.desde}:00`, `${ausencia.hasta}:00`, ausencia.motivo),
      `Ausencia programada para ${c.nombre}`,
    );
    setFormulario(false);
  };

  return (
    <li className={`rounded-xl border p-3 ${c.disponible ? 'border-slate-800 bg-slate-950/50' : 'border-red-500/30 bg-red-950/10'}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-white">{c.nombre}</p>
          <p className="text-slate-500">{c.cargo}</p>
        </div>
        <button
          onClick={alternar}
          className={`flex items-center gap-1 px-2 py-1 rounded-lg border cursor-pointer ${
            c.disponible ? 'border-emerald-500/40 text-emerald-300' : 'border-red-500/40 text-red-300'
          }`}
          title="Cambio manual de disponibilidad (excepción)"
        >
          {c.disponible ? <UserCheck className="w-3.5 h-3.5" /> : <UserX className="w-3.5 h-3.5" />}
          {c.disponible ? 'Disponible' : 'No disponible'}
        </button>
      </div>
      {!c.disponible && c.motivo_no_disponible && (
        <p className="text-red-300/80 mt-1">
          {c.motivo_no_disponible}
          {c.no_disponible_por_ausencia && <span className="text-slate-500"> · automático por calendario</span>}
        </p>
      )}
      <div className="mt-2 flex items-center gap-2">
        <span className="text-slate-500 w-12">Carga</span>
        <span className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
          <span
            className={`block h-full rounded-full ${ocupacion >= 1 ? 'bg-red-400' : 'bg-indigo-400'}`}
            style={{ width: `${Math.min(100, ocupacion * 100)}%` }}
          />
        </span>
        <span className="tabular-nums text-slate-300">
          {c.carga_actual}/{c.capacidad_max}
        </span>
        {ocupacion >= 1 && <AlertTriangle className="w-3.5 h-3.5 text-red-400" aria-label="Sin capacidad" />}
      </div>
      {c.historico.tareas > 0 && (
        <p className="text-slate-500 mt-1">
          Historial: {c.historico.tareas} tareas · {Math.round((c.historico.tasa_sla ?? 0) * 100)}% en SLA ·{' '}
          {c.historico.horas_promedio} h promedio
        </p>
      )}
      {proximas.map((a) => (
        <p key={a.desde} className="mt-1 flex items-center gap-1 text-amber-300/90">
          <CalendarOff className="w-3.5 h-3.5 shrink-0" /> {a.motivo}: {fecha(a.desde)} → {fecha(a.hasta)}
        </p>
      ))}
      {formulario ? (
        <div className="mt-2 grid grid-cols-2 gap-1.5">
          <label className="text-slate-500">
            Desde
            <input type="datetime-local" value={ausencia.desde} onChange={(e) => setAusencia({ ...ausencia, desde: e.target.value })} className={campo} />
          </label>
          <label className="text-slate-500">
            Hasta
            <input type="datetime-local" value={ausencia.hasta} onChange={(e) => setAusencia({ ...ausencia, hasta: e.target.value })} className={campo} />
          </label>
          <input
            value={ausencia.motivo}
            onChange={(e) => setAusencia({ ...ausencia, motivo: e.target.value })}
            className={`${campo} col-span-2`}
            aria-label="Motivo"
          />
          <Boton variante="primario" onClick={programar} disabled={!ausencia.desde || !ausencia.hasta}>
            Programar
          </Boton>
          <Boton onClick={() => setFormulario(false)}>Cancelar</Boton>
        </div>
      ) : (
        <button onClick={() => setFormulario(true)} className="mt-1.5 text-indigo-300 hover:text-indigo-200 cursor-pointer">
          + Programar ausencia
        </button>
      )}
    </li>
  );
};
