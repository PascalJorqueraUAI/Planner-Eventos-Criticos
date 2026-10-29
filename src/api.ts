/** Cliente de la API REST /api/v1 (server.ts). */
import type { DatosExtraidos, EstadoSistema } from './domain/types.js';

async function solicitar<T>(metodo: string, ruta: string, cuerpo?: unknown): Promise<T> {
  const resp = await fetch(`/api/v1${ruta}`, {
    method: metodo,
    headers: { 'Content-Type': 'application/json' },
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  });
  const datos = await resp.json();
  if (!resp.ok) throw new Error(datos.error || `Error ${resp.status}`);
  return datos as T;
}

/** Ejecuta una acción de la API, muestra lo que detectó el motor y refresca la Vista (ver App.tsx). */
export type Ejecutar = (accion: () => Promise<any>, exito?: string) => Promise<any>;

export const api = {
  estado: () => solicitar<EstadoSistema>('GET', '/estado'),
  escanear: () => solicitar<any>('POST', '/detector/escanear'),
  actualizarCaso: (id: string, cambios: Record<string, unknown>, usuario: string) =>
    solicitar<any>('PATCH', `/casos/${id}`, { cambios, usuario }),
  crearCaso: (caso: Record<string, string>, comprobante: { monto: number; canal: string } | null) =>
    solicitar<any>('POST', '/casos', { caso, comprobante }),
  ingresarAviso: (aviso: Record<string, unknown>, usuario: string) => solicitar<any>('POST', '/avisos', { aviso, usuario }),
  conciliarPlanilla: (registros: Record<string, unknown>[], usuario: string) =>
    solicitar<any>('POST', '/planillas-mandante', { registros, usuario }),
  extraerComprobante: (entrada: { texto: string; imagen_base64?: string; mime_type?: string; confirmacion_operador?: boolean }) =>
    solicitar<DatosExtraidos>('POST', '/extraer-comprobante', entrada),
  atenderTarea: (id: string, resultado: string, notas: string, usuario: string) =>
    solicitar<any>('POST', `/tareas/${id}/atender`, { resultado, notas, usuario }),
  reasignarTarea: (id: string, motivo: string) => solicitar<any>('POST', `/tareas/${id}/reasignar`, { motivo }),
  cambiarDisponibilidad: (id: string, disponible: boolean, motivo: string) =>
    solicitar<any>('PATCH', `/colaboradores/${id}/disponibilidad`, { disponible, motivo }),
  registrarAusencia: (id: string, desde: string, hasta: string, motivo: string) =>
    solicitar<any>('POST', `/colaboradores/${id}/ausencias`, { desde, hasta, motivo }),
  exportar: () => solicitar<{ archivos: string[] }>('POST', '/exportar'),
  reiniciar: (escenario?: string) => solicitar<any>('POST', '/reiniciar', { escenario }),
};
