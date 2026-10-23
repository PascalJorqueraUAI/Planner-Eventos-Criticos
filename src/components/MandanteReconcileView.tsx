import React, { useState } from 'react';
import {
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCw,
  Building,
  DollarSign,
  ArrowRight,
  Download,
  Info,
} from 'lucide-react';
import { PagoConciliado, AvisoPago, Caso } from '../domain/types.js';

interface MandanteReconcileViewProps {
  pagosConciliados: PagoConciliado[];
  avisos: AvisoPago[];
  casos: Caso[];
  onReconcileBatch: (lote: any[]) => Promise<any>;
}

const SAMPLE_MANDANTE_SHEET = [
  {
    rut: '16.482.910-K',
    monto: 850000,
    codigo_operacion: 'TRF-8849102',
    fecha_pago: '2026-10-23',
    mandante: 'Forum Servicios Financieros',
    cliente: 'Carlos Silva Mendoza',
    cuenta_abono: 'Cta Cte Santander 0-000-88419-2',
  },
  {
    rut: '18.291.433-2',
    monto: 450000,
    codigo_operacion: 'SAN-20261023-9941',
    fecha_pago: '2026-10-23',
    mandante: 'Banco Santander Chile',
    cliente: 'María José Contreras Pinto',
    cuenta_abono: 'Liquidación Central Santander',
  },
  {
    rut: '77.194.882-5',
    monto: 3500000,
    codigo_operacion: 'BCI-TRF-00192848',
    fecha_pago: '2026-10-22',
    mandante: 'Scotiabank Chile',
    cliente: 'Transportes San Cristóbal SpA',
    cuenta_abono: 'Cta Cte Scotiabank 11-0982-1',
  },
  {
    rut: '15.772.304-1',
    monto: 250000,
    codigo_operacion: 'SER-8812903',
    fecha_pago: '2026-10-21',
    mandante: 'Banco Falabella',
    cliente: 'Gonzalo Patricio Alarcón',
    cuenta_abono: 'Servipag / Recaudación CMR',
  },
];

export const MandanteReconcileView: React.FC<MandanteReconcileViewProps> = ({
  pagosConciliados,
  avisos,
  casos,
  onReconcileBatch,
}) => {
  const [running, setRunning] = useState(false);
  const [lastResult, setLastResult] = useState<any>(null);

  const handleRunReconcile = async () => {
    setRunning(true);
    try {
      const result = await onReconcileBatch(SAMPLE_MANDANTE_SHEET);
      setLastResult(result);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <FileSpreadsheet className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">
              Conciliación Periódica de Planillas de Mandantes
            </h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Cruza las planillas estructuradas que envían los bancos y entidades mandantes periódicamente contra los
              avisos y comprobantes no estructurados recibidos previamente.
            </p>
          </div>
        </div>

        <button
          disabled={running}
          onClick={handleRunReconcile}
          className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-4 py-2.5 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-emerald-600/30 transition cursor-pointer"
        >
          {running ? (
            <>
              <RotateCw className="w-4 h-4 animate-spin" />
              Conciliando en Python...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Ejecutar Conciliación Masiva con Python
            </>
          )}
        </button>
      </div>

      {/* Explanation Card from Cobgestion's document */}
      <div className="bg-indigo-950/30 border border-indigo-500/30 rounded-2xl p-4 text-xs text-indigo-200 flex items-start gap-3">
        <Info className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
        <div>
          <strong className="block text-white font-semibold mb-0.5">
            ¿Por qué separar avisos de pagos de los pagos conciliados?
          </strong>
          <span className="text-slate-300">
            Porque un pantallazo enviado por un cliente no tiene la misma validez que un pago formalmente liquidado por
            el mandante. Mantenerlos en tablas separadas permite actuar judicialmente de forma preventiva (frenando
            incautaciones indebidas) sin registrar contablemente un ingreso no verificado.
          </span>
        </div>
      </div>

      {/* Execution Results Notification */}
      {lastResult && (
        <div className="p-4 rounded-xl bg-emerald-950/70 border border-emerald-500/40 text-emerald-200 text-xs space-y-2">
          <div className="flex items-center gap-2 font-bold text-sm text-white">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            Conciliación completada por el Motor Python
          </div>
          <p>
            Se procesaron <strong>{SAMPLE_MANDANTE_SHEET.length}</strong> registros de planilla mandante.{' '}
            <strong>{lastResult.conciliados_exitosos}</strong> avisos fueron confirmados automáticamente.{' '}
            <strong>{lastResult.discrepancias_encontradas}</strong> situaciones requirieron observación.
          </p>
        </div>
      )}

      {/* Structured Mandante Liquidations Batch Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-md">
        <div className="p-4 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
          <span className="text-xs font-bold text-white uppercase tracking-wider">
            Planilla Estructurada del Mandante (Lote de Liquidación)
          </span>
          <span className="text-xs text-slate-400">
            {SAMPLE_MANDANTE_SHEET.length} registros cargados
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Mandante</th>
                <th className="py-3 px-4">Cliente / Deudor</th>
                <th className="py-3 px-4">RUT</th>
                <th className="py-3 px-4">Monto Liquidado</th>
                <th className="py-3 px-4">N° Operación</th>
                <th className="py-3 px-4">Fecha Pago</th>
                <th className="py-3 px-4">Estado en Cobgestion</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {SAMPLE_MANDANTE_SHEET.map((item, idx) => {
                const matchedAviso = avisos.find(
                  (a) =>
                    a.datosExtraidos.numeroOperacion === item.codigo_operacion ||
                    a.montoInformado === item.monto
                );

                return (
                  <tr key={idx} className="hover:bg-slate-850/50">
                    <td className="py-3 px-4 font-semibold text-white">{item.mandante}</td>
                    <td className="py-3 px-4">{item.cliente}</td>
                    <td className="py-3 px-4 font-mono text-indigo-300">{item.rut}</td>
                    <td className="py-3 px-4 font-bold text-emerald-400">
                      ${item.monto.toLocaleString('es-CL')} CLP
                    </td>
                    <td className="py-3 px-4 font-mono">{item.codigo_operacion}</td>
                    <td className="py-3 px-4">{item.fecha_pago}</td>
                    <td className="py-3 px-4">
                      {matchedAviso ? (
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                            matchedAviso.estadoVerificacion === 'confirmado'
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : 'bg-blue-500/20 text-blue-400'
                          }`}
                        >
                          Aviso {matchedAviso.id}: {matchedAviso.estadoVerificacion}
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-400">Sin aviso previo</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Reconciled Payments Table (Sheet: Pagos_Conciliados) */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-md">
        <div className="p-4 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
          <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            Tabla Central: Pagos_Conciliados ({pagosConciliados.length})
          </span>
          <span className="text-xs text-slate-400">
            Confirmados con respaldo del mandante
          </span>
        </div>

        {pagosConciliados.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            Aún no se han ejecutado conciliaciones masivas en esta sesión.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">ID Conciliación</th>
                  <th className="py-3 px-4">Caso ID</th>
                  <th className="py-3 px-4">Monto Conciliado</th>
                  <th className="py-3 px-4">Mandante</th>
                  <th className="py-3 px-4">Código Planilla</th>
                  <th className="py-3 px-4">Fecha Conciliación</th>
                  <th className="py-3 px-4">Conciliado Por</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {pagosConciliados.map((pago) => (
                  <tr key={pago.id} className="hover:bg-slate-850/50">
                    <td className="py-3 px-4 font-mono font-bold text-indigo-400">{pago.id}</td>
                    <td className="py-3 px-4 font-mono">{pago.casoId}</td>
                    <td className="py-3 px-4 font-bold text-emerald-400">
                      ${pago.montoConciliado.toLocaleString('es-CL')} CLP
                    </td>
                    <td className="py-3 px-4">{pago.mandante}</td>
                    <td className="py-3 px-4 font-mono text-slate-400">{pago.codigoPlanillaMandante}</td>
                    <td className="py-3 px-4">{pago.fechaConciliacion.slice(0, 16).replace('T', ' ')}</td>
                    <td className="py-3 px-4 text-slate-300 font-medium">{pago.conciliadoPor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
