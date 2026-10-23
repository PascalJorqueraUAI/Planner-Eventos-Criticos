import React, { useState } from 'react';
import {
  Sparkles,
  Upload,
  FileText,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  X,
  Car,
  ShieldAlert,
  Loader2,
  DollarSign,
  Building,
  Hash,
  User,
  Clock,
  Smartphone,
  Mail,
} from 'lucide-react';
import { Caso, AvisoPago } from '../domain/types.js';

interface UnstructuredIngestionModalProps {
  casos: Caso[];
  isOpen: boolean;
  onClose: () => void;
  onIngestComplete: (aviso: any, resultadoPython: any) => void;
}

const PRELOADED_SAMPLES = [
  {
    id: 'sample-1',
    title: 'Pantallazo WhatsApp: Carlos Silva (Auto Suzuki Swift BB-CL-44)',
    badge: 'Caso Real $600.000',
    badgeColor: 'bg-red-500/20 text-red-300 border-red-500/30',
    channel: 'WhatsApp',
    casoId: 'CASO-1052',
    monto: 850000,
    text: `Hola Camila buenas tardes, le acabo de transferir los $850.000 de la cuota y el compromiso de pago del auto Suzuki Swift patente BB-CL-44. Adjunto el pantallazo de Banco de Chile con la transferencia a la cuenta de Forum. Por favor avísele urgente al abogado para que frene la incautación del auto que me dijeron que venía mañana el receptor! Gracias.
Banco Origen: Banco de Chile
Banco Destino: Banco Santander (Forum Servicios Financieros)
Comprobante N°: TRF-8849102
RUT: 16.482.910-K
Titular: Carlos Silva Mendoza
Monto: $850.000 CLP
Fecha: 23/10/2026 08:15 hrs`,
    previewImageName: 'whatsapp_pantallazo_transferencia_carlos_silva.jpg',
  },
  {
    id: 'sample-2',
    title: 'Correo Automático Banco Santander: Transferencia Recibida',
    badge: 'Aviso Bancario Directo',
    badgeColor: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    channel: 'Email',
    casoId: 'CASO-1053',
    monto: 450000,
    text: `De: notificaciones@santander.cl
Para: cobranza@cobgestion.cl
Asunto: Aviso de Transferencia de Fondos - Banco Santander

Estimado cliente:
Le informamos que ha recibido una transferencia electrónica de fondos en su Cuenta Corriente N° 0-000-88419-2.
Detalle de la transferencia:
- Nombre Ordenante: María José Contreras Pinto
- RUT Ordenante: 18.291.433-2
- Banco Origen: Banco Santander Chile
- N° Operación: SAN-20261023-9941
- Monto: $450.000 CLP
- Glosa: Cuota convenio causa embargo C-8891-2025
- Fecha y hora: 23-10-2026 09:40:12`,
    previewImageName: 'correo_notificacion_santander.png',
  },
  {
    id: 'sample-3',
    title: 'Correo Cliente con Pantallazo: Transportes San Cristóbal SpA',
    badge: 'Riesgo Camión Tolva',
    badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    channel: 'Email',
    casoId: 'CASO-1054',
    monto: 3500000,
    text: `Estimados Cobgestion:
Adjunto comprobante de pago de la primera cuota de amortización por $3.500.000 del camión tolva Mercedes-Benz patente KR-WP-19 por la causa de Scotiabank. Por favor suspender diligencia del receptor judicial fijada para este viernes.
Transferencia realizada desde cuenta empresa Transportes San Cristóbal SpA, RUT 77.194.882-5.
Código transferencia BCI: BCI-TRF-00192848 por $3.500.000.`,
    previewImageName: 'comprobante_bci_transporte.png',
  },
  {
    id: 'sample-4',
    title: 'Recibo Servipag / Caja Vecina con Monto Menor (Observado)',
    badge: 'Discrepancia de Monto',
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
    channel: 'Portal Deudor',
    casoId: 'CASO-1055',
    monto: 250000,
    text: `Cliente Gonzalo Patricio Alarcón (RUT 15.772.304-1) sube comprobante escaneado de depósito en Servipag por $250.000. 
Causa: C-1102-2026 de Banco Falabella.
Monto acordado era $400.000 CLP. Comprobante Servipag N° 8812903.`,
    previewImageName: 'recibo_servipag_deposito.jpg',
  },
];

export const UnstructuredIngestionModal: React.FC<UnstructuredIngestionModalProps> = ({
  casos,
  isOpen,
  onClose,
  onIngestComplete,
}) => {
  const [selectedSampleId, setSelectedSampleId] = useState<string>('sample-1');
  const [inputText, setInputText] = useState<string>(PRELOADED_SAMPLES[0].text);
  const [canal, setCanal] = useState<string>('WhatsApp');
  const [origen, setOrigen] = useState<string>('Pantallazo cliente (WhatsApp)');
  const [selectedCasoId, setSelectedCasoId] = useState<string>('CASO-1052');
  const [imageFileName, setImageFileName] = useState<string>(PRELOADED_SAMPLES[0].previewImageName);

  // Extraction states
  const [extracting, setExtracting] = useState<boolean>(false);
  const [extractedData, setExtractedData] = useState<any>(null);
  const [ingesting, setIngesting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSelectSample = (sample: typeof PRELOADED_SAMPLES[0]) => {
    setSelectedSampleId(sample.id);
    setInputText(sample.text);
    setCanal(sample.channel);
    setSelectedCasoId(sample.casoId);
    setImageFileName(sample.previewImageName);
    setExtractedData(null);
  };

  const handleExtractWithAI = async () => {
    setExtracting(true);
    setErrorMsg(null);
    try {
      const resp = await fetch('/api/gemini/extract-receipt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: inputText,
        }),
      });
      const data = await resp.json();
      setExtractedData(data);

      // Auto-match case if RUT matches
      if (data.rut_depositante) {
        const cleanRut = data.rut_depositante.replace(/\./g, '').replace(/-/g, '').toUpperCase();
        const matched = casos.find((c) =>
          c.deudor.rut.replace(/\./g, '').replace(/-/g, '').toUpperCase().includes(cleanRut)
        );
        if (matched) {
          setSelectedCasoId(matched.id);
        }
      }
    } catch (err: any) {
      setErrorMsg('Error al extraer datos con Gemini AI: ' + err.message);
    } finally {
      setExtracting(false);
    }
  };

  const handleExecuteIngestionPython = async () => {
    if (!selectedCasoId) {
      setErrorMsg('Selecciona un caso judicial para vincular el comprobante');
      return;
    }

    setIngesting(true);
    setErrorMsg(null);

    const monto = extractedData?.monto || 850000;
    const avisoPayload = {
      id: `AVP-${Math.floor(100 + Math.random() * 900)}`,
      caso_id: selectedCasoId,
      fecha_recepcion: new Date().toISOString(),
      monto_informado: monto,
      origen,
      canal,
      estado_verificacion: 'informado',
      datos_extraidos: {
        banco_origen: extractedData?.banco_origen || 'Banco de Chile',
        banco_destino: extractedData?.banco_destino || 'Banco Santander',
        numero_operacion: extractedData?.numero_operacion || `TRF-${Math.floor(1000000 + Math.random() * 9000000)}`,
        rut_depositante: extractedData?.rut_depositante || '16.482.910-K',
        nombre_depositante: extractedData?.nombre_depositante || 'Carlos Silva Mendoza',
        fecha_hora_operacion: extractedData?.fecha_hora_operacion || new Date().toLocaleString('es-CL'),
        comentario: extractedData?.comentario || 'Ingresado vía asistente IA Cobgestion',
        confianza_ia: extractedData?.confianza_ia || 0.96,
      },
      archivo_comprobante: {
        nombre: imageFileName,
        tipo: 'image',
        preview_text: inputText.slice(0, 160) + '...',
      },
      observaciones_comerciales: 'Aviso recibido sin conciliar. Requiere revisión comercial contra cartola.',
      observaciones_judiciales: 'Alerta automática generada para revisión de apremios y medidas cautelares.',
    };

    try {
      const resp = await fetch('/api/ingest/notice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          aviso: avisoPayload,
          usuario: 'Ejecutiva Comercial (IA Ingestion)',
        }),
      });
      const result = await resp.json();
      if (result.error) throw new Error(result.error);

      onIngestComplete(avisoPayload, result);
      onClose();
    } catch (err: any) {
      setErrorMsg('Error al registrar aviso en Python: ' + err.message);
    } finally {
      setIngesting(false);
    }
  };

  const currentCaso = casos.find((c) => c.id === selectedCasoId);

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-6 shadow-2xl my-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 text-white shadow-lg shadow-indigo-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Ingreso Inteligente de Pagos No Estructurados
                <span className="text-xs bg-indigo-500/20 text-indigo-300 font-semibold px-2 py-0.5 rounded border border-indigo-500/30">
                  Gemini OCR + Motor Python
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Procesa pantallazos de WhatsApp, correos bancarios y transferencias, extrayendo datos y activando las
                alertas judiciales preventivas.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {errorMsg && (
          <div className="mt-4 p-3 rounded-xl bg-red-950/80 border border-red-500/50 text-red-200 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
            {errorMsg}
          </div>
        )}

        {/* Preloaded Samples Bar */}
        <div className="mt-4">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
            Seleccionar Caso Demostrativo Rápido (1 Clic)
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
            {PRELOADED_SAMPLES.map((sample) => (
              <button
                key={sample.id}
                onClick={() => handleSelectSample(sample)}
                className={`p-2.5 rounded-xl border text-left text-xs transition cursor-pointer flex flex-col justify-between ${
                  selectedSampleId === sample.id
                    ? 'bg-indigo-600/20 border-indigo-500 text-white shadow-md'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span
                      className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${sample.badgeColor}`}
                    >
                      {sample.badge}
                    </span>
                    <span className="text-[10px] text-slate-400">{sample.channel}</span>
                  </div>
                  <p className="font-semibold text-slate-200 text-xs line-clamp-1">{sample.title}</p>
                </div>
                <p className="text-emerald-400 font-bold text-xs mt-2">
                  ${sample.monto.toLocaleString('es-CL')} CLP
                </p>
              </button>
            ))}
          </div>
        </div>

        {/* Content Split: Input on Left, OCR Extraction on Right */}
        <div className="mt-5 grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Left Column (7 cols): Input & Case Selection */}
          <div className="lg:col-span-7 space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-slate-300">
                  Texto del Comprobante / Mensaje del Cliente o Banco
                </label>
                <span className="text-[10px] text-slate-400">Puedes editar o pegar cualquier comprobante</span>
              </div>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                rows={6}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 font-mono leading-relaxed focus:outline-none focus:border-indigo-500"
                placeholder="Pegar texto de transferencia, correo electrónico o mensaje de WhatsApp..."
              />
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block text-slate-400 font-medium mb-1">Canal de Recepción</label>
                <select
                  value={canal}
                  onChange={(e) => setCanal(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="WhatsApp">WhatsApp (Pantallazo / Foto)</option>
                  <option value="Email">Correo Electrónico</option>
                  <option value="Portal Deudor">Portal Web Deudor</option>
                  <option value="Planilla Mandante">Planilla Mandante</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 font-medium mb-1">Expediente / Caso Vinculado</label>
                <select
                  value={selectedCasoId}
                  onChange={(e) => setSelectedCasoId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500"
                >
                  {casos.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.id} - {c.deudor.nombre} ({c.rolCausa})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Selected Case Preview Badge */}
            {currentCaso && (
              <div
                className={`p-3 rounded-xl border text-xs ${
                  currentCaso.bienEnGarantia.tipo === 'Vehículo' &&
                  currentCaso.estadoJudicial === 'Orden de incautación vigente'
                    ? 'bg-red-950/40 border-red-500/40 text-red-200'
                    : 'bg-slate-950 border-slate-800 text-slate-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold flex items-center gap-1.5">
                    {currentCaso.bienEnGarantia.tipo === 'Vehículo' && (
                      <Car className="w-4 h-4 text-amber-400" />
                    )}
                    {currentCaso.deudor.nombre} &bull; ROL {currentCaso.rolCausa}
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-700">
                    {currentCaso.mandante}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Estado judicial:{' '}
                  <strong className="text-amber-400">{currentCaso.estadoJudicial}</strong> &bull; Bien:{' '}
                  {currentCaso.bienEnGarantia.descripcion}
                </p>
              </div>
            )}

            <button
              disabled={extracting}
              onClick={handleExtractWithAI}
              className="w-full bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white font-bold py-2.5 px-4 rounded-xl text-xs flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/30 transition cursor-pointer"
            >
              {extracting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Extrayendo datos estructurados con Gemini AI...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Paso 1: Analizar & Extraer Datos con IA (Gemini 3.8 Flash)
                </>
              )}
            </button>
          </div>

          {/* Right Column (5 cols): AI Extracted Preview */}
          <div className="lg:col-span-5 bg-slate-950 rounded-xl p-4 border border-slate-800 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-xs font-bold text-white flex items-center gap-1.5">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  Datos Estructurados por IA
                </span>
                {extractedData && (
                  <span className="text-[10px] text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    {Math.round((extractedData.confianza_ia || 0.96) * 100)}% Certidumbre
                  </span>
                )}
              </div>

              {!extractedData ? (
                <div className="py-12 text-center text-slate-400 text-xs">
                  <Sparkles className="w-8 h-8 text-indigo-400/60 mx-auto mb-2 animate-pulse" />
                  <p className="font-semibold text-slate-300">Extracción pendiente</p>
                  <p className="text-[11px] mt-1 text-slate-400">
                    Haz clic en &quot;Paso 1: Analizar con IA&quot; para ejecutar el OCR y parseo automático de banco,
                    monto, RUT y operación.
                  </p>
                </div>
              ) : (
                <div className="mt-3 space-y-2.5 text-xs">
                  <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-[10px] text-slate-400 block uppercase font-bold">Monto Detectado</span>
                    <span className="text-lg font-bold text-emerald-400">
                      ${Number(extractedData.monto || 0).toLocaleString('es-CL')} CLP
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-slate-900 p-2 rounded-lg border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase font-bold">Banco Origen</span>
                      <strong className="text-slate-200 text-xs">
                        {extractedData.banco_origen || 'No informado'}
                      </strong>
                    </div>
                    <div className="bg-slate-900 p-2 rounded-lg border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase font-bold">N° Operación</span>
                      <strong className="text-indigo-400 font-mono text-xs">
                        {extractedData.numero_operacion || 'TRF-S/N'}
                      </strong>
                    </div>
                  </div>

                  <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-[10px] text-slate-400 block uppercase font-bold">Depositante & RUT</span>
                    <p className="text-slate-200 font-semibold">
                      {extractedData.nombre_depositante || 'Carlos Silva'} &bull;{' '}
                      <span className="font-mono text-indigo-300">{extractedData.rut_depositante || 'N/A'}</span>
                    </p>
                  </div>

                  {extractedData.resumen_ejecutivo && (
                    <div className="p-2.5 rounded-lg bg-indigo-950/40 border border-indigo-500/30 text-indigo-200 text-[11px]">
                      {extractedData.resumen_ejecutivo}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Step 2 Ingest Button */}
            <div className="pt-4 border-t border-slate-800 mt-4">
              <button
                disabled={!extractedData || ingesting}
                onClick={handleExecuteIngestionPython}
                className={`w-full font-bold py-3 px-4 rounded-xl text-xs flex items-center justify-center gap-2 transition cursor-pointer shadow-lg ${
                  extractedData && !ingesting
                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/30'
                    : 'bg-slate-800 text-slate-400 cursor-not-allowed'
                }`}
              >
                {ingesting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Ejecutando Detector Python...
                  </>
                ) : (
                  <>
                    <ShieldAlert className="w-4 h-4" />
                    Paso 2: Disparar Detección de Evento Crítico en Python
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
