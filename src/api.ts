/** Cliente de la API REST /api/v1 (server.ts). */
import type { CuentasDemo, DatosExtraidos, EstadoSistema, Usuario } from './domain/types.js';

/** La sesión expiró o no existe: la Vista vuelve a la pantalla de inicio. */
export class SinSesion extends Error {}

async function solicitar<T>(metodo: string, ruta: string, cuerpo?: unknown): Promise<T> {
  const resp = await fetch(`/api/v1${ruta}`, {
    method: metodo,
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  });
  const datos = await resp.json();
  if (resp.status === 401) throw new SinSesion(datos.error);
  if (!resp.ok) throw new Error(datos.error || `Error ${resp.status}`);
  return datos as T;
}

/** Ejecuta una acción de la API, muestra lo que detectó el motor y refresca la Vista (ver App.tsx). */
export type Ejecutar = (accion: () => Promise<any>, exito?: string) => Promise<any>;

export const api = {
  iniciarSesion: (email: string, clave: string) => solicitar<Usuario>('POST', '/sesion', { email, clave }),
  cerrarSesion: () => solicitar<{ ok: boolean }>('DELETE', '/sesion'),
  cuentasDemo: () => solicitar<CuentasDemo>('GET', '/sesion/demo'),
  leerNotificaciones: (ids?: string[]) => solicitar<{ marcadas: number }>('POST', '/notificaciones/leer', { ids: ids ?? null }),
  estado: () => solicitar<EstadoSistema>('GET', '/estado'),
  escanear: () => solicitar<any>('POST', '/detector/escanear'),
  actualizarCaso: (id: string, cambios: Record<string, unknown>) => solicitar<any>('PATCH', `/casos/${id}`, { cambios }),
  crearCaso: (caso: Record<string, string>, comprobante: { monto: number; canal: string } | null) =>
    solicitar<any>('POST', '/casos', { caso, comprobante }),
  ingresarAviso: (aviso: Record<string, unknown>) => solicitar<any>('POST', '/avisos', { aviso }),
  conciliarPlanilla: (registros: Record<string, unknown>[]) => solicitar<any>('POST', '/planillas-mandante', { registros }),
  extraerComprobante: (entrada: { texto: string; imagen_base64?: string; mime_type?: string; confirmacion_operador?: boolean }) =>
    solicitar<DatosExtraidos>('POST', '/extraer-comprobante', entrada),
  atenderTarea: (id: string, resultado: string, notas: string) =>
    solicitar<any>('POST', `/tareas/${id}/atender`, { resultado, notas }),
  reasignarTarea: (id: string, motivo: string) => solicitar<any>('POST', `/tareas/${id}/reasignar`, { motivo }),
  cambiarDisponibilidad: (id: string, disponible: boolean, motivo: string) =>
    solicitar<any>('PATCH', `/colaboradores/${id}/disponibilidad`, { disponible, motivo }),
  registrarAusencia: (id: string, desde: string, hasta: string, motivo: string) =>
    solicitar<any>('POST', `/colaboradores/${id}/ausencias`, { desde, hasta, motivo }),
  exportar: () => solicitar<{ archivos: string[] }>('POST', '/exportar'),
  reiniciar: (escenario?: string) => solicitar<any>('POST', '/reiniciar', { escenario }),
};
