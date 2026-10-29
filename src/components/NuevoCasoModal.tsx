import React, { useState } from 'react';
import { X, Loader2, FilePlus2, ShieldAlert, UserX, CheckCircle2, ArrowRight } from 'lucide-react';
import { api, type Ejecutar } from '../api.js';
import type { EstadoSistema, PartidaRiesgo, Prioridad } from '../domain/types.js';
import { BadgePrioridad, Boton, DesgloseRiesgo, Etiqueta, campo, clp } from './ui.js';

interface ResumenTarea {
  id: string;
  area: string;
  titulo: string;
  sla_horas: number;
  responsable: string;
  puntaje: number | null;
  escalada: boolean;
  candidatos: { nombre: string; puntaje: number }[];
  excluidos: { nombre: string; motivo: string }[];
}

interface ResumenEvento {
  id: string;
  codigo: string;
  nombre: string;
  prioridad: Prioridad;
  motivo: string;
  riesgo_clp: number;
  riesgo_detalle: PartidaRiesgo[];
  tareas: ResumenTarea[];
}

type Formulario = Record<
  | 'rol_causa' | 'tribunal' | 'deudor_nombre' | 'deudor_rut' | 'mandante' | 'monto_deuda' | 'bien_tipo'
  | 'bien_descripcion' | 'bien_patente' | 'estado_comercial' | 'estado_judicial' | 'responsable_comercial'
  | 'responsable_judicial' | 'fecha_diligencia',
  string
>;

/** RUT ficticio con dígito verificador válido (módulo 11), para los ejemplos. */
function rutAleatorio(): string {
  const numero = 10_000_000 + Math.floor(Math.random() * 15_000_000);
  let suma = 0;
  let factor = 2;
  for (const digito of String(numero).split('').reverse()) {
    suma += Number(digito) * factor;
    factor = factor === 7 ? 2 : factor + 1;
  }
  const resto = 11 - (suma % 11);
  const dv = resto === 11 ? '0' : resto === 10 ? 'K' : String(resto);
  return `${numero.toLocaleString('es-CL')}-${dv}`;
}

const enHoras = (horas: number) => {
  const d = new Date(Date.now() + horas * 3_600_000);
  d.setMinutes(0, 0, 0);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:00`;
};

const rolAleatorio = () => `C-${1000 + Math.floor(Math.random() * 9000)}-2026`;

interface Ejemplo {
  titulo: string;
  explicacion: string;
  caso: Partial<Formulario>;
  comprobante: number | null;
}

const EJEMPLOS: Ejemplo[] = [
  {
    titulo: 'Auto con incautación + comprobante',
    explicacion: 'Debería generar EC-01 crítico: Judicial con 4 h para revisar la incautación.',
    caso: {
      estado_comercial: 'En negociación', estado_judicial: 'Orden de incautación vigente', bien_tipo: 'Vehículo',
      bien_descripcion: 'Automóvil Mazda 3 2021', monto_deuda: '6.200.000', mandante: 'Forum Servicios Financieros',
    },
    comprobante: 900000,
  },
  {
    titulo: 'Diligencia en 48 h con negociación',
    explicacion: 'Debería generar EC-04: confirmar la diligencia y contactar al deudor antes.',
    caso: {
      estado_comercial: 'En negociación', estado_judicial: 'Diligencia con receptor programada', bien_tipo: 'Vehículo',
      bien_descripcion: 'Camioneta Nissan Navara 2020', monto_deuda: '9.800.000', mandante: 'Banco BCI',
    },
    comprobante: null,
  },
  {
    titulo: 'Caso sin riesgo (control)',
    explicacion: 'No debería generar eventos: sin apremio ni pagos pendientes.',
    caso: {
      estado_comercial: 'Sin contacto', estado_judicial: 'Notificado', bien_tipo: 'Sin garantía',
      bien_descripcion: 'Crédito de consumo', monto_deuda: '780.000', mandante: 'Banco Falabella',
    },
    comprobante: null,
  },
];

const VACIO: Formulario = {
  rol_causa: '', tribunal: '', deudor_nombre: '', deudor_rut: '', mandante: '', monto_deuda: '', bien_tipo: 'Sin garantía',
  bien_descripcion: '', bien_patente: '', estado_comercial: 'En negociación', estado_judicial: 'Notificado',
  responsable_comercial: '', responsable_judicial: '', fecha_diligencia: '',
};

interface Props {
  estado: EstadoSistema;
  abierto: boolean;
  onCerrar: () => void;
  ejecutar: Ejecutar;
  irAAsignacion: () => void;
}

export const NuevoCasoModal: React.FC<Props> = ({ estado, abierto, onCerrar, ejecutar, irAAsignacion }) => {
  const [form, setForm] = useState<Formulario>(VACIO);
  const [conComprobante, setConComprobante] = useState(false);
  const [montoComprobante, setMontoComprobante] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultado, setResultado] = useState<{ casoId: string; eventos: ResumenEvento[] } | null>(null);

  if (!abierto) return null;

  const ejecutivos = (cargo: string) => estado.colaboradores.filter((c) => c.cargo === cargo);
  const cambiar = (campoForm: keyof Formulario, valor: string) => setForm((f) => ({ ...f, [campoForm]: valor }));

  const usarEjemplo = (ejemplo: Ejemplo, indice: number) => {
    // Titulares: el primero con cargo de ejecutivo de cada área (puede estar no disponible: así se ve la exclusión).
    const comercial = ejecutivos('Ejecutivo Comercial')[0]?.id ?? '';
    const judicial = ejecutivos('Ejecutivo Judicial')[0]?.id ?? '';
    setForm({
      ...VACIO,
      ...ejemplo.caso,
      rol_causa: rolAleatorio(),
      tribunal: `${10 + indice}° Juzgado Civil de Santiago`,
      deudor_nombre: `Deudor de prueba ${Math.floor(Math.random() * 900) + 100}`,
      deudor_rut: rutAleatorio(),
      bien_patente: ejemplo.caso.bien_tipo === 'Vehículo' ? `PR-${String.fromCharCode(65 + indice)}${String.fromCharCode(75 + indice)}-${10 + indice * 7}` : '',
      responsable_comercial: comercial,
      responsable_judicial: judicial,
      fecha_diligencia: ejemplo.caso.estado_judicial === 'Diligencia con receptor programada' ? enHoras(48) : '',
    });
    setConComprobante(ejemplo.comprobante !== null);
    setMontoComprobante(ejemplo.comprobante ? String(ejemplo.comprobante) : '');
    setError(null);
  };

  const crear = async () => {
    setEnviando(true);
    setError(null);
    try {
      const comprobante = conComprobante ? { monto: Number(montoComprobante.replace(/\D/g, '')), canal: 'WhatsApp' } : null;
      const r = await ejecutar(() => api.crearCaso(form, comprobante), 'Caso creado');
      setResultado({ casoId: r.caso.id, eventos: r.eventos_del_caso });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  };

  const cerrar = () => {
    setResultado(null);
    setForm(VACIO);
    setError(null);
    onCerrar();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-start sm:items-center justify-center p-3 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <FilePlus2 className="w-5 h-5 text-indigo-300" /> Nuevo caso
            </h2>
            <p className="text-xs text-slate-400">
              Al crearlo, el detector lo compara con el catálogo de eventos críticos y el asignador reparte las tareas en el
              acto. En operación los casos llegan desde el CRM (API o importación CSV); este formulario sirve para cargas puntuales
              y para la demo.
            </p>
          </div>
          <button onClick={cerrar} className="p-1 text-slate-400 hover:text-white cursor-pointer" aria-label="Cerrar">
            <X className="w-5 h-5" />
          </button>
        </div>

        {resultado ? (
          <ResultadoCreacion resultado={resultado} onOtro={() => setResultado(null)} onVer={() => { cerrar(); irAAsignacion(); }} />
        ) : (
          <>
            <div className="mt-4">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-2">Ejemplos de un clic</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {EJEMPLOS.map((e, i) => (
                  <button
                    key={e.titulo}
                    onClick={() => usarEjemplo(e, i)}
                    className="text-left rounded-lg border border-slate-800 bg-slate-950 hover:border-indigo-500 p-2.5 cursor-pointer"
                  >
                    <p className="text-xs font-semibold text-slate-200">{e.titulo}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">{e.explicacion}</p>
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <p className="mt-3 text-xs text-red-300 bg-red-950/40 border border-red-500/40 rounded-lg px-3 py-2">{error}</p>
            )}

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <fieldset className="space-y-2">
                <legend className="font-semibold text-slate-200 mb-1">Causa y deudor</legend>
                <div className="grid grid-cols-2 gap-2">
                  <Campo etiqueta="Rol de la causa" valor={form.rol_causa} onCambiar={(v) => cambiar('rol_causa', v)} />
                  <Campo etiqueta="Tribunal" valor={form.tribunal} onCambiar={(v) => cambiar('tribunal', v)} />
                  <Campo etiqueta="Deudor" valor={form.deudor_nombre} onCambiar={(v) => cambiar('deudor_nombre', v)} />
                  <Campo etiqueta="RUT del deudor" valor={form.deudor_rut} onCambiar={(v) => cambiar('deudor_rut', v)} mono />
                  <Campo etiqueta="Mandante" valor={form.mandante} onCambiar={(v) => cambiar('mandante', v)} />
                  <Campo etiqueta="Monto de la deuda" valor={form.monto_deuda} onCambiar={(v) => cambiar('monto_deuda', v)} />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <label className="block text-slate-400">
                    Bien en garantía
                    <select value={form.bien_tipo} onChange={(e) => cambiar('bien_tipo', e.target.value)} className={`${campo} mt-1`}>
                      {['Vehículo', 'Inmueble', 'Bienes muebles', 'Maquinaria', 'Sin garantía'].map((t) => (
                        <option key={t}>{t}</option>
                      ))}
                    </select>
                  </label>
                  <Campo etiqueta="Descripción" valor={form.bien_descripcion} onCambiar={(v) => cambiar('bien_descripcion', v)} />
                  <Campo etiqueta="Patente" valor={form.bien_patente} onCambiar={(v) => cambiar('bien_patente', v)} mono />
                </div>
              </fieldset>

              <fieldset className="space-y-2">
                <legend className="font-semibold text-slate-200 mb-1">Estado y responsables titulares</legend>
                <div className="grid grid-cols-2 gap-2">
                  <label className="block text-slate-400">
                    Estado comercial
                    <select value={form.estado_comercial} onChange={(e) => cambiar('estado_comercial', e.target.value)} className={`${campo} mt-1`}>
                      {estado.estados.comercial.map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-slate-400">
                    Estado judicial
                    <select value={form.estado_judicial} onChange={(e) => cambiar('estado_judicial', e.target.value)} className={`${campo} mt-1`}>
                      {estado.estados.judicial.map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                  </label>
                  {(['Comercial', 'Judicial'] as const).map((area) => {
                    const clave = area === 'Comercial' ? 'responsable_comercial' : 'responsable_judicial';
                    return (
                      <label key={area} className="block text-slate-400">
                        Titular {area.toLowerCase()}
                        <select value={form[clave]} onChange={(e) => cambiar(clave, e.target.value)} className={`${campo} mt-1`}>
                          <option value="">Elegir…</option>
                          {ejecutivos(`Ejecutivo ${area}`).map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.nombre}
                              {c.disponible ? '' : ' (no disponible)'}
                            </option>
                          ))}
                        </select>
                      </label>
                    );
                  })}
                </div>
                <label className="block text-slate-400">
                  Fecha de la próxima diligencia (opcional)
                  <input
                    type="datetime-local"
                    value={form.fecha_diligencia}
                    onChange={(e) => cambiar('fecha_diligencia', e.target.value)}
                    className={`${campo} mt-1`}
                  />
                </label>
                <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 space-y-2">
                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                    <input type="checkbox" checked={conComprobante} onChange={(e) => setConComprobante(e.target.checked)} />
                    Ya llegó un comprobante de pago (queda en estado <strong>informado</strong>)
                  </label>
                  {conComprobante && (
                    <Campo etiqueta="Monto del comprobante" valor={montoComprobante} onCambiar={setMontoComprobante} />
                  )}
                </div>
              </fieldset>
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <Boton onClick={cerrar}>Cancelar</Boton>
              <Boton variante="peligro" onClick={crear} disabled={enviando}>
                {enviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldAlert className="w-4 h-4" />}
                Crear caso y ejecutar detector
              </Boton>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const Campo: React.FC<{ etiqueta: string; valor: string; onCambiar: (v: string) => void; mono?: boolean }> = ({
  etiqueta,
  valor,
  onCambiar,
  mono,
}) => (
  <label className="block text-slate-400">
    {etiqueta}
    <input value={valor} onChange={(e) => onCambiar(e.target.value)} className={`${campo} mt-1 ${mono ? 'font-mono' : ''}`} />
  </label>
);

const ResultadoCreacion: React.FC<{
  resultado: { casoId: string; eventos: ResumenEvento[] };
  onOtro: () => void;
  onVer: () => void;
}> = ({ resultado, onOtro, onVer }) => (
  <div className="mt-4 space-y-3 text-xs">
    <p className="flex items-center gap-2 text-emerald-300 font-semibold text-sm">
      <CheckCircle2 className="w-5 h-5" /> {resultado.casoId} creado en el repositorio
    </p>
    {resultado.eventos.length === 0 ? (
      <p className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-slate-300">
        El detector no encontró eventos críticos: el caso no cumple ninguna regla del catálogo (por ejemplo, no tiene un
        apremio en curso ni un pago pendiente de verificar). Si después cambia su estado, el detector lo volverá a evaluar.
      </p>
    ) : (
      resultado.eventos.map((e) => (
        <article
          key={e.id}
          className={`rounded-xl border p-3 space-y-2 ${e.prioridad === 'CRITICA' ? 'border-red-500/40 bg-red-950/20' : 'border-slate-700 bg-slate-950/60'}`}
        >
          <div className="flex flex-wrap items-center gap-2">
            <Etiqueta tono="indigo">{e.codigo}</Etiqueta>
            <BadgePrioridad prioridad={e.prioridad} />
            <span className="font-bold text-white text-sm">{e.nombre}</span>
            {e.riesgo_clp > 0 && <span className="text-red-300">riesgo {clp(e.riesgo_clp)}</span>}
          </div>
          <p className="text-slate-400">{e.motivo}</p>
          <DesgloseRiesgo partidas={e.riesgo_detalle} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {e.tareas.map((t) => (
              <div key={t.id} className="rounded-lg border border-slate-800 bg-slate-900 p-2.5 space-y-1">
                <div className="flex items-center gap-2">
                  <Etiqueta tono={t.area === 'Judicial' ? 'indigo' : 'emerald'}>{t.area}</Etiqueta>
                  <span className="text-slate-500">SLA {t.sla_horas} h</span>
                  {t.escalada && <Etiqueta tono="red">Escalada a jefatura</Etiqueta>}
                </div>
                <p className="text-slate-200">{t.titulo}</p>
                <p className="text-slate-300">
                  Asignada a <strong className="text-white">{t.responsable}</strong>
                  {t.puntaje != null && <span className="text-slate-500"> · puntaje {t.puntaje.toFixed(2)}</span>}
                </p>
                {t.candidatos.length > 1 && (
                  <p className="text-slate-500">
                    Otros candidatos: {t.candidatos.slice(1).map((c) => `${c.nombre} (${c.puntaje.toFixed(2)})`).join(', ')}
                  </p>
                )}
                {t.excluidos.map((x) => (
                  <p key={x.nombre} className="text-slate-500 flex items-start gap-1">
                    <UserX className="w-3.5 h-3.5 text-red-400 shrink-0 mt-px" /> {x.nombre}: {x.motivo}
                  </p>
                ))}
              </div>
            ))}
          </div>
        </article>
      ))
    )}
    <div className="flex justify-end gap-2">
      <Boton onClick={onOtro}>Crear otro caso</Boton>
      {resultado.eventos.length > 0 && (
        <Boton variante="primario" onClick={onVer}>
          Ver en Asignación y seguimiento <ArrowRight className="w-4 h-4" />
        </Boton>
      )}
    </div>
  </div>
);
