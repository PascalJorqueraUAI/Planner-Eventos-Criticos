/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useCallback, useEffect, useState } from 'react';
import { Header, type Modulo } from './components/Header.js';
import { RepositorioView } from './components/RepositorioView.js';
import { DetectorView } from './components/DetectorView.js';
import { AsignacionView } from './components/AsignacionView.js';
import { DashboardView } from './components/DashboardView.js';
import { Login } from './components/Login.js';
import { BandejaCorreos } from './components/BandejaCorreos.js';
import { api, SinSesion } from './api.js';
import type { EstadoSistema } from './domain/types.js';

const INTERVALO_REFRESCO_MS = 15_000;
const MODULOS: Modulo[] = ['repositorio', 'detector', 'asignacion', 'dashboard'];

const moduloDesdeUrl = (): Modulo => {
  const hash = window.location.hash.slice(1) as Modulo;
  return MODULOS.includes(hash) ? hash : 'repositorio';
};

/** #correos abre la bandeja; #correos/MAIL-0001 abre ese correo. */
const correoDesdeUrl = (): string | null | undefined => {
  const hash = window.location.hash.slice(1);
  if (!hash.startsWith('correos')) return undefined;
  return hash.split('/')[1] ?? null;
};

export default function App() {
  const [modulo, setModuloEstado] = useState<Modulo>(moduloDesdeUrl);
  const setModulo = (m: Modulo) => {
    window.location.hash = m;
    setModuloEstado(m);
  };
  // undefined = bandeja cerrada · null = abierta sin correo elegido · string = correo abierto
  const [correo, setCorreo] = useState<string | null | undefined>(correoDesdeUrl);
  const [estado, setEstado] = useState<EstadoSistema | null>(null);
  const [sinSesion, setSinSesion] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    const alCambiar = () => setCorreo(correoDesdeUrl());
    window.addEventListener('hashchange', alCambiar);
    return () => window.removeEventListener('hashchange', alCambiar);
  }, []);

  const refrescar = useCallback(async () => {
    try {
      setEstado(await api.estado());
      setSinSesion(false);
      setError(null);
    } catch (e: any) {
      if (e instanceof SinSesion) {
        setSinSesion(true);
        setEstado(null);
      } else setError(e.message);
    }
  }, []);

  useEffect(() => {
    if (sinSesion) return;
    refrescar();
    const id = setInterval(refrescar, INTERVALO_REFRESCO_MS);
    return () => clearInterval(id);
  }, [refrescar, sinSesion]);

  /** Ejecuta una acción contra la API, informa los eventos que detectó y refresca el estado. */
  const ejecutar = useCallback(
    async (accion: () => Promise<any>, exito?: string) => {
      try {
        const r = await accion();
        const nuevos = r?.deteccion?.eventos_nuevos ?? [];
        const escaladas = r?.deteccion?.tareas_escaladas ?? [];
        const reasignadas = r?.reasignadas ?? [];
        const notificadas = r?.notificaciones_enviadas ?? 0;
        const partes = [
          exito,
          nuevos.length ? `Detector: ${nuevos.map((e: any) => `${e.codigo} ${e.nombre}`).join(' · ')}` : '',
          reasignadas.length ? `${reasignadas.length} tarea(s) reasignada(s) automáticamente` : '',
          escaladas.length ? `${escaladas.length} tarea(s) vencida(s) escalada(s)` : '',
          notificadas ? `${notificadas} notificación(es) enviada(s)` : '',
        ].filter(Boolean);
        if (partes.length) setAviso(partes.join(' — '));
        await refrescar();
        return r;
      } catch (e: any) {
        if (e instanceof SinSesion) setSinSesion(true);
        setAviso(`Error: ${e.message}`);
        throw e;
      }
    },
    [refrescar],
  );

  useEffect(() => {
    if (!aviso) return;
    const id = setTimeout(() => setAviso(null), 7000);
    return () => clearTimeout(id);
  }, [aviso]);

  const reiniciar = (escenario: string) => {
    if (confirm(`¿Recargar el sandbox con el escenario «${escenario}»? Se perderán los cambios hechos en la demo.`)) {
      ejecutar(() => api.reiniciar(escenario), `Sandbox reiniciado (escenario ${escenario})`);
    }
  };

  const cerrarSesion = async () => {
    await api.cerrarSesion();
    setEstado(null);
    setSinSesion(true);
  };

  const leerNotificaciones = async (ids?: string[]) => {
    await api.leerNotificaciones(ids);
    await refrescar();
  };

  const abrirCorreo = (id: string | null) => {
    window.location.hash = id ? `correos/${id}` : 'correos';
  };
  const cerrarBandeja = () => {
    window.location.hash = modulo;
  };

  if (sinSesion) return <Login onIngreso={() => setSinSesion(false)} />;

  if (!estado) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-slate-400">
        {error ? `No se pudo conectar con la API: ${error}` : 'Cargando repositorio…'}
      </div>
    );
  }

  return (
    <div className="min-h-screen text-slate-100 flex flex-col">
      <Header
        activo={modulo}
        onCambiar={setModulo}
        estado={estado}
        onReiniciar={reiniciar}
        onLeerNotificaciones={leerNotificaciones}
        onAbrirCorreo={abrirCorreo}
        onCerrarSesion={cerrarSesion}
      />

      <main className="flex-1 min-w-0 max-w-7xl w-full mx-auto px-3 py-4 sm:px-4 md:py-6">
        {modulo === 'repositorio' && (
          <RepositorioView estado={estado} ejecutar={ejecutar} irAAsignacion={() => setModulo('asignacion')} />
        )}
        {modulo === 'detector' && <DetectorView estado={estado} ejecutar={ejecutar} irATareas={() => setModulo('asignacion')} />}
        {modulo === 'asignacion' && <AsignacionView estado={estado} ejecutar={ejecutar} />}
        {modulo === 'dashboard' && <DashboardView estado={estado} />}
      </main>

      {correo !== undefined && (
        <BandejaCorreos
          correos={estado.correos}
          seleccionado={correo}
          todos={estado.sesion.permisos.ver_todos_los_correos}
          onSeleccionar={abrirCorreo}
          onCerrar={cerrarBandeja}
        />
      )}

      {aviso && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 max-w-xl w-[calc(100%-2rem)] bg-slate-900 border border-indigo-500/50 text-slate-100 text-xs rounded-xl px-4 py-3 shadow-2xl">
          {aviso}
        </div>
      )}

      <footer className="border-t border-slate-800/80 py-3 px-4 text-[11px] text-slate-500 text-center">
        Vista React · API REST /api/v1 · Motor Python (Modelo + Controlador) · Último escaneo del detector:{' '}
        {estado.ultimo_escaneo ? new Date(estado.ultimo_escaneo).toLocaleTimeString('es-CL') : '—'}
      </footer>
    </div>
  );
}
