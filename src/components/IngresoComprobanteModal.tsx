import React, { useState } from 'react';
import { Sparkles, X, Loader2, ShieldAlert, ShieldCheck, ImageUp, FileText, Lock } from 'lucide-react';
import { api, type Ejecutar } from '../api.js';
import type { Caso, ConfigExtraccion, DatosExtraidos } from '../domain/types.js';
import { Boton, campo, clp } from './ui.js';

/** Comprobantes reales de ejemplo, tal como llegan a Cobgestion (sin estructura). */
const EJEMPLOS = [
  {
    titulo: 'Correo cliente: camión KR-WP-19',
    canal: 'Email',
    origen: 'Correo cliente con pantallazo',
    texto: `Estimados Cobgestion:
Adjunto comprobante de pago de la primera cuota por $3.500.000 del camión tolva Mercedes-Benz patente KR-WP-19 (causa Scotiabank). Por favor suspender la diligencia del receptor fijada para esta semana.
Transferencia desde cuenta de Transportes San Cristóbal SpA, RUT 77.194.882-5.
Código transferencia BCI: BCI-TRF-00192848`,
  },
  {
    titulo: 'Aviso automático Banco Santander',
    canal: 'Email',
    origen: 'Correo automático banco',
    texto: `De: notificaciones@santander.cl
Asunto: Aviso de transferencia de fondos
Nombre ordenante: María José Contreras Pinto
RUT ordenante: 18.291.433-2
N° Operación: SAN-20261026-1187
Monto: $50.000
Glosa: diferencia cuota convenio C-8891-2025`,
  },
  {
    titulo: 'WhatsApp sin N° de operación',
    canal: 'WhatsApp',
    origen: 'Pantallazo cliente (WhatsApp)',
    texto: `Hola, soy Gonzalo Patricio Alarcón, le hice el depósito en Servipag por $250.000 para la deuda con Banco Falabella. Mi correo es g.alarcon@gmail.com y mi fono +56 9 7721 8891. Mándeme la confirmación porfa.`,
  },
];

const LADO_MAXIMO_PX = 1600;

/**
 * Re-dibuja la imagen en un canvas: el JPEG resultante no conserva metadatos EXIF
 * (GPS, dispositivo, fecha de la foto) y se reduce al tamaño necesario para leerla.
 */
async function recodificarImagen(archivo: File): Promise<string> {
  const mapa = await createImageBitmap(archivo);
  const escala = Math.min(1, LADO_MAXIMO_PX / Math.max(mapa.width, mapa.height));
  const lienzo = document.createElement('canvas');
  lienzo.width = Math.round(mapa.width * escala);
  lienzo.height = Math.round(mapa.height * escala);
  lienzo.getContext('2d')!.drawImage(mapa, 0, 0, lienzo.width, lienzo.height);
  mapa.close();
  return lienzo.toDataURL('image/jpeg', 0.85);
}

interface Formulario {
  caso_id: string;
  monto: string;
  rut_depositante: string;
  numero_operacion: string;
  banco_origen: string;
  nombre_depositante: string;
}

const VACIO: Formulario = { caso_id: '', monto: '', rut_depositante: '', numero_operacion: '', banco_origen: '', nombre_depositante: '' };

interface Props {
  casos: Caso[];
  config: ConfigExtraccion;
  abierto: boolean;
  onCerrar: () => void;
  ejecutar: Ejecutar;
}

export const IngresoComprobanteModal: React.FC<Props> = ({ casos, config, abierto, onCerrar, ejecutar }) => {
  const [fuente, setFuente] = useState<'texto' | 'imagen'>('texto');
  const [texto, setTexto] = useState(EJEMPLOS[0].texto);
  const [canal, setCanal] = useState(EJEMPLOS[0].canal);
  const [origen, setOrigen] = useState(EJEMPLOS[0].origen);
  const [imagen, setImagen] = useState<string | null>(null);
  const [confirmacion, setConfirmacion] = useState(false);
  const [extraccion, setExtraccion] = useState<DatosExtraidos | null>(null);
  const [form, setForm] = useState<Formulario>(VACIO);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!abierto) return null;

  const reiniciarResultado = () => {
    setExtraccion(null);
    setForm(VACIO);
    setError(null);
  };

  const elegirEjemplo = (i: number) => {
    setFuente('texto');
    setTexto(EJEMPLOS[i].texto);
    setCanal(EJEMPLOS[i].canal);
    setOrigen(EJEMPLOS[i].origen);
    reiniciarResultado();
  };

  const cargarImagen = async (archivo?: File) => {
    if (!archivo) return;
    reiniciarResultado();
    setConfirmacion(false);
    setImagen(await recodificarImagen(archivo));
    setCanal('WhatsApp');
    setOrigen('Pantallazo cliente (imagen)');
  };

  const extraer = async () => {
    setCargando(true);
    setError(null);
    try {
      const datos = await api.extraerComprobante(
        fuente === 'imagen' && imagen
          ? { texto: '', imagen_base64: imagen, mime_type: 'image/jpeg', confirmacion_operador: confirmacion }
          : { texto },
      );
      setExtraccion(datos);
      setForm((f) => ({
        caso_id: f.caso_id,
        monto: datos.monto ? String(datos.monto) : '',
        rut_depositante: datos.rut_depositante ?? '',
        numero_operacion: datos.numero_operacion ?? '',
        banco_origen: datos.banco_origen ?? '',
        nombre_depositante: datos.nombre_depositante ?? '',
      }));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  };

  const registrar = async () => {
    setCargando(true);
    try {
      await ejecutar(
        () =>
          api.ingresarAviso(
            {
              caso_id: form.caso_id || undefined,
              monto: Number(form.monto.replace(/\D/g, '')),
              canal,
              origen,
              datos_extraidos: {
                rut_depositante: form.rut_depositante || null,
                numero_operacion: form.numero_operacion || null,
                banco_origen: form.banco_origen || null,
                nombre_depositante: form.nombre_depositante || null,
                // Trazabilidad sin guardar el comprobante: con qué se extrajo y su huella.
                motor_extraccion: extraccion?.motor_extraccion ?? 'manual',
                hash_comprobante: extraccion?.hash_comprobante ?? null,
                revisado_por_operador: true,
              },
              observaciones: extraccion ? `Datos extraídos (${extraccion.motor_extraccion}) y revisados por el operador.` : 'Ingresado a mano.',
            },
            'Ingesta de comprobantes',
          ),
        'Comprobante registrado en el repositorio',
      );
      setImagen(null);
      reiniciarResultado();
      onCerrar();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  };

  const imagenSinConfirmar = fuente === 'imagen' && config.gemini_activo && !confirmacion;
  const puedeExtraer = fuente === 'texto' ? texto.trim().length > 0 : Boolean(imagen) && config.gemini_activo && confirmacion;
  const puedeRegistrar = Number(form.monto.replace(/\D/g, '')) > 0 && Boolean(form.caso_id || form.rut_depositante);

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-start sm:items-center justify-center p-3 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <h2 className="text-base font-bold text-white">Registrar comprobante de pago</h2>
            <p className="text-xs text-slate-400">
              Completa los datos a mano o usa la extracción como ayuda. El aviso queda <strong>informado</strong> y el detector
              alerta a Judicial de inmediato.
            </p>
          </div>
          <button onClick={onCerrar} className="p-1 text-slate-400 hover:text-white cursor-pointer" aria-label="Cerrar">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div
          className={`mt-3 rounded-lg border px-3 py-2 text-[11px] flex items-start gap-2 ${
            config.gemini_activo ? 'border-indigo-500/30 bg-indigo-500/5 text-indigo-200' : 'border-slate-700 bg-slate-950 text-slate-400'
          }`}
        >
          {config.gemini_activo ? <ShieldCheck className="w-4 h-4 shrink-0" /> : <Lock className="w-4 h-4 shrink-0" />}
          <span>
            {config.motivo}
            {config.gemini_activo && ` Modelo: ${config.modelo}.`}
          </span>
        </div>

        {error && <p className="mt-3 text-xs text-red-300 bg-red-950/40 border border-red-500/40 rounded-lg px-3 py-2">{error}</p>}

        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Fuente del comprobante */}
          <div className="space-y-3">
            <div className="flex gap-2 text-xs">
              <button
                onClick={() => setFuente('texto')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border cursor-pointer ${
                  fuente === 'texto' ? 'bg-indigo-600/20 border-indigo-500 text-white' : 'border-slate-700 text-slate-400'
                }`}
              >
                <FileText className="w-4 h-4" /> Texto (correo, mensaje)
              </button>
              <button
                onClick={() => setFuente('imagen')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border cursor-pointer ${
                  fuente === 'imagen' ? 'bg-indigo-600/20 border-indigo-500 text-white' : 'border-slate-700 text-slate-400'
                }`}
              >
                <ImageUp className="w-4 h-4" /> Imagen (pantallazo)
              </button>
            </div>

            {fuente === 'texto' ? (
              <>
                <div className="flex flex-wrap gap-1.5">
                  {EJEMPLOS.map((e, i) => (
                    <button
                      key={e.titulo}
                      onClick={() => elegirEjemplo(i)}
                      className="text-[11px] px-2 py-1 rounded-md border border-slate-800 bg-slate-950 text-slate-400 hover:text-white cursor-pointer"
                    >
                      {e.titulo}
                    </button>
                  ))}
                </div>
                <textarea
                  value={texto}
                  onChange={(e) => {
                    setTexto(e.target.value);
                    reiniciarResultado();
                  }}
                  rows={8}
                  className={`${campo} font-mono leading-relaxed`}
                  aria-label="Texto del comprobante"
                />
              </>
            ) : (
              <div className="space-y-2 text-xs">
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => cargarImagen(e.target.files?.[0])}
                  className="block w-full text-slate-300 file:mr-3 file:px-3 file:py-1.5 file:rounded-lg file:border-0 file:bg-slate-800 file:text-slate-200"
                />
                {imagen && <img src={imagen} alt="Comprobante cargado" className="max-h-56 rounded-lg border border-slate-800 mx-auto" />}
                {!config.gemini_activo ? (
                  <p className="text-slate-400">
                    La lectura de imágenes requiere Gemini, que no está habilitado. Mira el pantallazo y completa los datos a
                    mano: la imagen no sale del navegador.
                  </p>
                ) : (
                  <label className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-2.5 text-amber-100 cursor-pointer">
                    <input type="checkbox" checked={confirmacion} onChange={(e) => setConfirmacion(e.target.checked)} className="mt-0.5" />
                    <span>
                      Confirmo que la imagen contiene <strong>solo el comprobante</strong> y que enviarla a Google (Gemini, fuera
                      de Chile) es necesario para verificar este pago. La imagen se envía sin metadatos, no se almacena y el
                      envío queda en el registro de tratamientos.
                    </span>
                  </label>
                )}
              </div>
            )}

            <Boton variante="primario" className="w-full" onClick={extraer} disabled={cargando || !puedeExtraer}>
              {cargando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              Extraer datos (opcional)
            </Boton>
            {imagenSinConfirmar && imagen && <p className="text-[11px] text-amber-300">Confirma el envío para extraer con Gemini.</p>}

            {extraccion && (
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-[11px] space-y-1">
                <p className="text-slate-300">
                  <strong>{extraccion.motor_extraccion === 'Gemini' ? 'Gemini' : 'Extracción local'}</strong> · {extraccion.motivo}
                </p>
                {extraccion.datos_enviados != null && (
                  <details className="text-slate-500">
                    <summary className="cursor-pointer text-slate-400">Ver exactamente qué texto salió hacia Gemini</summary>
                    <pre className="mt-1 whitespace-pre-wrap font-mono text-slate-400">{extraccion.datos_enviados || '(solo la imagen)'}</pre>
                  </details>
                )}
              </div>
            )}
          </div>

          {/* Formulario de registro: siempre editable */}
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs space-y-2.5">
            <p className="font-bold text-slate-200">Datos del pago {extraccion && <span className="font-normal text-slate-500">(revisa antes de registrar)</span>}</p>
            <label className="block text-slate-400">
              Caso
              <select value={form.caso_id} onChange={(e) => setForm({ ...form, caso_id: e.target.value })} className={`${campo} mt-1`}>
                <option value="">Asociar automáticamente por RUT</option>
                {casos.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.id} · {c.deudor.nombre}
                  </option>
                ))}
              </select>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label className="block text-slate-400">
                Monto (CLP)
                <input value={form.monto} onChange={(e) => setForm({ ...form, monto: e.target.value })} inputMode="numeric" className={`${campo} mt-1`} />
              </label>
              <label className="block text-slate-400">
                RUT depositante
                <input value={form.rut_depositante} onChange={(e) => setForm({ ...form, rut_depositante: e.target.value })} className={`${campo} mt-1 font-mono`} />
              </label>
              <label className="block text-slate-400">
                N° de operación
                <input value={form.numero_operacion} onChange={(e) => setForm({ ...form, numero_operacion: e.target.value })} className={`${campo} mt-1 font-mono`} />
              </label>
              <label className="block text-slate-400">
                Banco
                <input value={form.banco_origen} onChange={(e) => setForm({ ...form, banco_origen: e.target.value })} className={`${campo} mt-1`} />
              </label>
            </div>
            <label className="block text-slate-400">
              Nombre del depositante
              <input value={form.nombre_depositante} onChange={(e) => setForm({ ...form, nombre_depositante: e.target.value })} className={`${campo} mt-1`} />
            </label>
            <label className="block text-slate-400">
              Canal
              <select value={canal} onChange={(e) => setCanal(e.target.value)} className={`${campo} mt-1`}>
                {['WhatsApp', 'Email', 'Portal Deudor', 'API Banco'].map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            {Number(form.monto.replace(/\D/g, '')) > 0 &&
              (puedeRegistrar ? (
                <p className="text-emerald-300">Se registrará un aviso por {clp(Number(form.monto.replace(/\D/g, '')))} en estado informado.</p>
              ) : (
                <p className="text-amber-300">Elige el caso o indica el RUT del depositante para asociar el pago.</p>
              ))}
            <Boton variante="peligro" className="w-full" onClick={registrar} disabled={!puedeRegistrar || cargando}>
              <ShieldAlert className="w-4 h-4" /> Registrar y ejecutar detector
            </Boton>
          </div>
        </div>
      </div>
    </div>
  );
};
