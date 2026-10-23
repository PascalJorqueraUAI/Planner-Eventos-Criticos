import React, { useState } from 'react';
import {
  Activity,
  ShieldCheck,
  Clock,
  Car,
  DollarSign,
  TrendingUp,
  FileText,
  Search,
  Filter,
  ArrowRight,
  Database,
  Cpu,
  Layers,
} from 'lucide-react';
import { AuditoriaHistorial, Caso, EventoCritico, TareaParalela } from '../domain/types.js';

interface TraceabilityDashboardProps {
  historial: AuditoriaHistorial[];
  eventos: EventoCritico[];
  casos: Caso[];
  tareas: TareaParalela[];
  ahorroEstimadoCLP: number;
}

export const TraceabilityDashboard: React.FC<TraceabilityDashboardProps> = ({
  historial,
  eventos,
  casos,
  tareas,
  ahorroEstimadoCLP,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [areaFilter, setAreaFilter] = useState<string>('todos');

  const filteredHistory = historial.filter((item) => {
    const matchesArea = areaFilter === 'todos' || item.area === areaFilter;
    const matchesSearch =
      item.detalles.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.accion.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.usuario.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.casoId.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesArea && matchesSearch;
  });

  const totalEventos = eventos.length;
  const cerrados = eventos.filter((e) => e.cerrado).length;
  const tasaExito = totalEventos > 0 ? Math.round((cerrados / totalEventos) * 100) : 100;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Dashboard de Trazabilidad & Métricas Capstone</h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Auditoría integral con timestamps, registro inmutable de decisiones entre áreas y cuantificación de costos
              judiciales prevenidos.
            </p>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Pérdidas Prevenidas
            </span>
            <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400">
              <Car className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black text-emerald-400">
            ${ahorroEstimadoCLP.toLocaleString('es-CL')} CLP
          </p>
          <p className="text-[11px] text-slate-400 mt-1">
            Costas judiciales de incautación y grúa evitadas mediante alerta preventiva.
          </p>
        </div>

        {/* Metric 2 */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Eventos Críticos
            </span>
            <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black text-white">
            {eventos.filter((e) => !e.cerrado).length} <span className="text-sm font-normal text-slate-400">activos</span>
          </p>
          <p className="text-[11px] text-slate-400 mt-1">
            {cerrados} eventos cerrados con resolución coordinada de ambas áreas.
          </p>
        </div>

        {/* Metric 3 */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Tasa de Coordinación
            </span>
            <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black text-cyan-400">{tasaExito}%</p>
          <p className="text-[11px] text-slate-400 mt-1">
            0 casos con desfasaje comercial-judicial sin resolución oportuna.
          </p>
        </div>

        {/* Metric 4 */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Tiempo Reacción Judicial
            </span>
            <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black text-amber-300">&lt; 2.5 hrs</p>
          <p className="text-[11px] text-slate-400 mt-1">
            Cumplimiento estricto del SLA de 4 horas para casos vehiculares en riesgo.
          </p>
        </div>
      </div>

      {/* Visual System Architecture Diagram (Matching Capstone Diagram) */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <Layers className="w-4 h-4 text-indigo-400" />
          Flujo de Integración en Tiempo Real (Arquitectura Cobgestion)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
            <div>
              <span className="text-[10px] text-indigo-400 font-bold uppercase block mb-1">
                1. Ingreso de Datos
              </span>
              <p className="font-bold text-white">Comercial & Judicial</p>
              <p className="text-slate-400 text-[11px] mt-1">
                Comprobantes WhatsApp, transferencias banco y estados procesales ingresan al repositorio.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-slate-850 flex items-center gap-1 text-slate-500 text-[10px]">
              Actualiza caso &rarr;
            </div>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-indigo-500/30 flex flex-col justify-between">
            <div>
              <span className="text-[10px] text-indigo-400 font-bold uppercase block mb-1">
                2. Repositorio Central
              </span>
              <p className="font-bold text-white">Base Estructurada</p>
              <p className="text-slate-400 text-[11px] mt-1">
                6 entidades conectadas por ID único de caso (Casos, Avisos, Pagos, Eventos, Tareas, Historial).
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-slate-850 flex items-center gap-1 text-slate-500 text-[10px]">
              Lectura de datos &rarr;
            </div>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-amber-500/30 flex flex-col justify-between">
            <div>
              <span className="text-[10px] text-amber-400 font-bold uppercase block mb-1">
                3. Detector Python
              </span>
              <p className="font-bold text-white">Reglas Automatizadas</p>
              <p className="text-slate-400 text-[11px] mt-1">
                Identifica riesgos de incautación activa y dispara eventos críticos en paralelo.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-slate-850 flex items-center gap-1 text-slate-500 text-[10px]">
              Detecta conflicto &rarr;
            </div>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-emerald-500/30 flex flex-col justify-between">
            <div>
              <span className="text-[10px] text-emerald-400 font-bold uppercase block mb-1">
                4. Asignación Paralela
              </span>
              <p className="font-bold text-white">Recepción de Alertas</p>
              <p className="text-slate-400 text-[11px] mt-1">
                Notifica simultáneamente a Judicial (suspender apremio) y Comercial (verificar pago).
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-slate-850 flex items-center gap-1 text-emerald-400 text-[10px] font-bold">
              Bloqueo de cierre hasta doble OK
            </div>
          </div>
        </div>
      </div>

      {/* Audit Log Table (Historial) */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-md">
        <div className="p-4 bg-slate-950/80 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-indigo-400" />
            <span className="text-xs font-bold text-white uppercase tracking-wider">
              Trazabilidad Completa (Historial de Auditoría)
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs">
            {/* Search */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Buscar en auditoría..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Filter */}
            <select
              value={areaFilter}
              onChange={(e) => setAreaFilter(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
            >
              <option value="todos">Todas las Áreas</option>
              <option value="Judicial">Judicial</option>
              <option value="Comercial">Comercial</option>
              <option value="Sistema IA">Sistema IA / Python</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Fecha y Hora</th>
                <th className="py-3 px-4">Área</th>
                <th className="py-3 px-4">Usuario / Actor</th>
                <th className="py-3 px-4">Acción Realizada</th>
                <th className="py-3 px-4">Caso / Evento</th>
                <th className="py-3 px-4">Detalle y Trazabilidad</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {filteredHistory.map((item) => (
                <tr key={item.id} className="hover:bg-slate-850/50">
                  <td className="py-3 px-4 font-mono text-slate-400 whitespace-nowrap">
                    {item.timestamp.slice(0, 19).replace('T', ' ')}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                        item.area === 'Judicial'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : item.area === 'Comercial'
                          ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      }`}
                    >
                      {item.area}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-medium text-white whitespace-nowrap">{item.usuario}</td>
                  <td className="py-3 px-4 font-semibold text-slate-200">{item.accion}</td>
                  <td className="py-3 px-4 font-mono text-indigo-400">{item.casoId}</td>
                  <td className="py-3 px-4 text-slate-300 max-w-md">{item.detalles}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
