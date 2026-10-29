import React, { useMemo, useState } from 'react';
import { Database, FileSpreadsheet, Upload, Download, History, RefreshCw, Car, FilePlus2 } from 'lucide-react';
import { api, type Ejecutar } from '../api.js';
import type { EstadoSistema } from '../domain/types.js';
import { IngresoComprobanteModal } from './IngresoComprobanteModal.js';
import { NuevoCasoModal } from './NuevoCasoModal.js';
import { Boton, Etiqueta, Tarjeta, TituloSeccion, campo, clp, fecha, relativo, tonoEstadoPago } from './ui.js';

/** Planilla quincenal de ejemplo enviada por los mandantes (dato estructurado). */
const PLANILLA_EJEMPLO = [
  { rut: '16.482.910-K', monto: 850000, codigo_operacion: 'TRF-8849102', fecha_pago: '2026-10-23', mandante: 'Forum Servicios Financieros' },
  { rut: '18.291.433-2', monto: 450000, codigo_operacion: 'SAN-20261023-9941', fecha_pago: '2026-10-23', mandante: 'Banco Santander Chile' },
  { rut: '15.772.304-1', monto: 250000, codigo_operacion: 'SER-8812903', fecha_pago: '2026-10-21', mandante: 'Banco Falabella' },
  { rut: '9.115.302-4', monto: 120000, codigo_operacion: 'FAL-0091221', fecha_pago: '2026-10-21', mandante: 'Banco Falabella' },
];

interface Props {
  estado: EstadoSistema;
  ejecutar: Ejecutar;
  irAAsignacion: () => void;
}

export const RepositorioView: React.FC<Props> = ({ estado, ejecutar, irAAsignacion }) => {
  const [seleccionado, setSeleccionado] = useState<string>(estado.casos[0]?.id);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [nuevoCasoAbierto, setNuevoCasoAbierto] = useState(false);
  const [planillaAbierta, setPlanillaAbierta] = useState(false);
  const [resultadoPlanilla, setResultadoPlanilla] = useState<any>(null);

  const nombre = useMemo(
    () => Object.fromEntries(estado.colaboradores.map((c) => [c.id, c.nombre])),
    [estado.colaboradores],
  );
  const caso = estado.casos.find((c) => c.id === seleccionado);

  const conciliar = async () => {
    const r = await ejecutar(() => api.conciliarPlanilla(PLANILLA_EJEMPLO, 'Planilla mandante'), 'Planilla conciliada');
    setResultadoPlanilla(r.conciliacion);
  };

  const exportar = () =>
    ejecutar(async () => {
      const r = await api.exportar();
      return { ...r, deteccion: null };
    }, 'Hojas exportadas a la carpeta exports/ (CSV para Excel)');

  return (
    <div className="space-y-5">
      <Tarjeta>
        <TituloSeccion
          icono={<Database className="w-5 h-5" />}
          titulo="1 · Repositorio centralizado"
          subtitulo="Planilla única con el estado actual de cada caso, sus últimas actualizaciones y el historial de cambios. Se alimenta del CRM, de los comprobantes y de las planillas de mandantes."
          acciones={
            <>
              <Boton variante="primario" onClick={() => setNuevoCasoAbierto(true)}>
                <FilePlus2 className="w-4 h-4" /> Nuevo caso
              </Boton>
              <Boton variante="primario" onClick={() => setModalAbierto(true)}>
                <Upload className="w-4 h-4" /> Registrar comprobante
              </Boton>
              <Boton onClick={() => setPlanillaAbierta((v) => !v)}>
                <FileSpreadsheet className="w-4 h-4" /> Planilla de mandante
              </Boton>
              <Boton onClick={exportar}>
                <Download className="w-4 h-4" /> Exportar a Excel
              </Boton>
            </>
          }
        />

        {planillaAbierta && (
          <div className="p-4 border-b border-slate-800 bg-slate-950/50 text-xs space-y-3">
            <p className="text-slate-300">
              Planilla estructurada recibida de los mandantes. Se cruza por N° de operación o RUT + monto contra los avisos
              pendientes; un pago sin aviso previo se registra como confirmado.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px]">
                <thead className="text-slate-500 text-left">
                  <tr>
                    <th className="py-1 font-medium">Mandante</th>
                    <th className="font-medium">RUT</th>
                    <th className="font-medium">Operación</th>
                    <th className="font-medium text-right">Monto</th>
                  </tr>
                </thead>
                <tbody>
                  {PLANILLA_EJEMPLO.map((r) => (
                    <tr key={r.codigo_operacion} className="border-t border-slate-800">
                      <td className="py-1">{r.mandante}</td>
                      <td className="font-mono">{r.rut}</td>
                      <td className="font-mono">{r.codigo_operacion}</td>
                      <td className="text-right">{clp(r.monto)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Boton variante="primario" onClick={conciliar}>
                <RefreshCw className="w-4 h-4" /> Conciliar planilla
              </Boton>
              {resultadoPlanilla && (
                <span className="text-slate-300">
                  {resultadoPlanilla.confirmados.length} confirmados · {resultadoPlanilla.observados.length} observados ·{' '}
                  {resultadoPlanilla.nuevos.length} pagos sin aviso previo · {resultadoPlanilla.sin_caso.length} sin caso asociado
                </span>
              )}
            </div>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-xs">
            <thead className="text-slate-500 text-left border-b border-slate-800">
              <tr>
                <th className="px-4 py-2 font-medium">Caso / Rol</th>
                <th className="px-2 font-medium">Deudor · Mandante</th>
                <th className="px-2 font-medium">Estado comercial</th>
                <th className="px-2 font-medium">Estado judicial</th>
                <th className="px-2 font-medium">Pagos</th>
                <th className="px-2 font-medium">Eventos</th>
                <th className="px-2 font-medium">Titulares</th>
                <th className="px-4 font-medium">Última actualización</th>
              </tr>
            </thead>
            <tbody>
              {estado.casos.map((c) => {
                const avisos = estado.avisos.filter((a) => a.caso_id === c.id);
                const abiertos = estado.eventos.filter((e) => e.caso_id === c.id && e.estado === 'Abierto');
                return (
                  <tr
                    key={c.id}
                    onClick={() => setSeleccionado(c.id)}
                    className={`border-b border-slate-800/70 cursor-pointer hover:bg-slate-800/40 ${
                      seleccionado === c.id ? 'bg-indigo-500/10' : ''
                    }`}
                  >
                    <td className="px-4 py-2.5">
                      <p className="font-semibold text-white">{c.id}</p>
                      <p className="text-slate-500 font-mono">{c.rol_causa}</p>
                    </td>
                    <td className="px-2">
                      <p className="text-slate-200 flex items-center gap-1">
                        {c.bien_garantia.tipo === 'Vehículo' && <Car className="w-3.5 h-3.5 text-amber-400" />}
                        {c.deudor.nombre}
                      </p>
                      <p className="text-slate-500">{c.mandante}</p>
                    </td>
                    <td className="px-2 text-slate-300">{c.estado_comercial}</td>
                    <td className="px-2 text-slate-300">{c.estado_judicial}</td>
                    <td className="px-2">
                      <div className="flex flex-wrap gap-1">
                        {avisos.length === 0 && <span className="text-slate-600">—</span>}
                        {avisos.map((a) => (
                          <Etiqueta key={a.id} tono={tonoEstadoPago(a.estado)}>
                            {a.estado}
                          </Etiqueta>
                        ))}
                      </div>
                    </td>
                    <td className="px-2">
                      {abiertos.length ? <Etiqueta tono="red">{abiertos.length} abierto(s)</Etiqueta> : <span className="text-slate-600">—</span>}
                    </td>
                    <td className="px-2 text-slate-400">
                      <p>{nombre[c.responsable_comercial]}</p>
                      <p>{nombre[c.responsable_judicial]}</p>
                    </td>
                    <td className="px-4 text-slate-400 whitespace-nowrap">{relativo(c.ultima_actualizacion, estado.ahora)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Tarjeta>

      {caso && <DetalleCaso key={caso.id} estado={estado} casoId={caso.id} nombre={nombre} ejecutar={ejecutar} />}

      <NuevoCasoModal
        estado={estado}
        abierto={nuevoCasoAbierto}
        onCerrar={() => setNuevoCasoAbierto(false)}
        ejecutar={ejecutar}
        irAAsignacion={irAAsignacion}
      />

      <IngresoComprobanteModal
        casos={estado.casos}
        config={estado.extraccion}
        abierto={modalAbierto}
        onCerrar={() => setModalAbierto(false)}
        ejecutar={ejecutar}
      />
    </div>
  );
};

const DetalleCaso: React.FC<{
  estado: EstadoSistema;
  casoId: string;
  nombre: Record<string, string>;
  ejecutar: Ejecutar;
}> = ({ estado, casoId, nombre, ejecutar }) => {
  const caso = estado.casos.find((c) => c.id === casoId)!;
  const [form, setForm] = useState({
    estado_comercial: caso.estado_comercial,
    estado_judicial: caso.estado_judicial,
    fecha_diligencia: caso.fecha_diligencia?.slice(0, 16) ?? '',
  });
  const avisos = estado.avisos.filter((a) => a.caso_id === casoId);
  const historial = estado.historial.filter((h) => h.caso_id === casoId);

  const enviar = () => {
    const cambios: Record<string, unknown> = {};
    if (form.estado_comercial !== caso.estado_comercial) cambios.estado_comercial = form.estado_comercial;
    if (form.estado_judicial !== caso.estado_judicial) cambios.estado_judicial = form.estado_judicial;
    const diligencia = form.fecha_diligencia ? `${form.fecha_diligencia}:00` : null;
    if (diligencia !== caso.fecha_diligencia) cambios.fecha_diligencia = diligencia;
    if (Object.keys(cambios).length === 0) return;
    ejecutar(() => api.actualizarCaso(casoId, cambios, 'Integración CRM'), `Caso ${casoId} actualizado vía API`);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
      <Tarjeta className="lg:col-span-2 p-4 space-y-4 text-xs">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-500">Expediente</p>
          <h3 className="text-base font-bold text-white">
            {caso.id} · {caso.deudor.nombre}
          </h3>
          <p className="text-slate-400">
            {caso.rol_causa} · {caso.tribunal}
          </p>
          <p className="text-slate-400 mt-1">
            Deuda {clp(caso.monto_deuda)} · {caso.bien_garantia.descripcion}
            {caso.bien_garantia.patente && ` (${caso.bien_garantia.patente})`}
          </p>
          {caso.fecha_diligencia && <p className="text-amber-300 mt-1">Diligencia: {fecha(caso.fecha_diligencia)}</p>}
        </div>

        <div>
          <p className="font-semibold text-slate-200 mb-1.5">Avisos de pago</p>
          {avisos.length === 0 && <p className="text-slate-500">Sin avisos registrados.</p>}
          <ul className="space-y-1.5">
            {avisos.map((a) => (
              <li key={a.id} className="bg-slate-950 border border-slate-800 rounded-lg p-2">
                <div className="flex justify-between gap-2">
                  <span className="font-mono text-slate-300">{a.id}</span>
                  <Etiqueta tono={tonoEstadoPago(a.estado)}>{a.estado}</Etiqueta>
                </div>
                <p className="text-slate-400 mt-0.5">
                  {clp(a.monto)} · {a.canal} · {fecha(a.fecha_recepcion)}
                </p>
                {a.observaciones && <p className="text-slate-500 mt-0.5">{a.observaciones}</p>}
              </li>
            ))}
          </ul>
        </div>

        <div className="border-t border-slate-800 pt-3 space-y-2">
          <p className="font-semibold text-slate-200">Actualización desde el CRM (PATCH /api/v1/casos/{caso.id})</p>
          <p className="text-slate-500">
            Simula el cambio que enviaría el sistema actual de Cobgestion. El detector se ejecuta al recibirlo.
          </p>
          <select value={form.estado_comercial} onChange={(e) => setForm({ ...form, estado_comercial: e.target.value })} className={campo} aria-label="Estado comercial">
            {estado.estados.comercial.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select value={form.estado_judicial} onChange={(e) => setForm({ ...form, estado_judicial: e.target.value })} className={campo} aria-label="Estado judicial">
            {estado.estados.judicial.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <label className="block text-slate-400">
            Fecha de diligencia
            <input
              type="datetime-local"
              value={form.fecha_diligencia}
              onChange={(e) => setForm({ ...form, fecha_diligencia: e.target.value })}
              className={`${campo} mt-1`}
            />
          </label>
          <Boton variante="primario" className="w-full" onClick={enviar}>
            Enviar actualización
          </Boton>
        </div>
      </Tarjeta>

      <Tarjeta className="lg:col-span-3">
        <TituloSeccion
          icono={<History className="w-5 h-5" />}
          titulo="Historial de cambios del caso"
          subtitulo={`Responsables titulares: ${nombre[caso.responsable_comercial]} (Comercial) · ${nombre[caso.responsable_judicial]} (Judicial)`}
        />
        <ol className="p-4 space-y-2.5 max-h-[520px] overflow-y-auto text-xs">
          {historial.length === 0 && <li className="text-slate-500">Sin cambios registrados.</li>}
          {historial.map((h) => (
            <li key={h.id} className="border-l-2 border-slate-700 pl-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-slate-500 font-mono">{fecha(h.timestamp)}</span>
                <Etiqueta tono={h.area === 'Judicial' ? 'indigo' : h.area === 'Comercial' ? 'emerald' : 'slate'}>{h.area}</Etiqueta>
                <span className="font-semibold text-slate-200">{h.accion}</span>
              </div>
              <p className="text-slate-400 mt-0.5">{h.detalle}</p>
              <p className="text-slate-600">por {h.usuario}</p>
            </li>
          ))}
        </ol>
      </Tarjeta>
    </div>
  );
};
