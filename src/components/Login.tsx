import React, { useEffect, useState } from 'react';
import { LogIn, Loader2, ShieldCheck } from 'lucide-react';
import { api } from '../api.js';
import type { CuentasDemo, Nivel } from '../domain/types.js';
import { Boton, campo } from './ui.js';

const NIVELES: { nivel: Nivel; titulo: string; detalle: string }[] = [
  { nivel: 1, titulo: 'Nivel 1 · Gerencia general', detalle: 'Acceso completo' },
  { nivel: 2, titulo: 'Nivel 2 · Gerencias de área', detalle: 'Su área y la operación general' },
  { nivel: 3, titulo: 'Nivel 3 · Ejecutivos y abogados', detalle: 'Sus tareas; datos personales solo de sus casos' },
];

export const Login: React.FC<{ onIngreso: () => void }> = ({ onIngreso }) => {
  const [email, setEmail] = useState('');
  const [clave, setClave] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);
  const [demo, setDemo] = useState<CuentasDemo | null>(null);

  useEffect(() => {
    api.cuentasDemo().then(setDemo).catch(() => setDemo({ modo_demo: false }));
  }, []);

  const entrar = async (correo: string, contrasena: string) => {
    setCargando(true);
    setError(null);
    try {
      await api.iniciarSesion(correo, contrasena);
      onIngreso();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-5 gap-5">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            entrar(email, clave);
          }}
          className="md:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-4 self-start"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-white font-black">
              C
            </div>
            <div>
              <p className="text-base font-bold text-white leading-tight">Cobgestion · Eventos Críticos</p>
              <p className="text-[11px] text-slate-400">Inicia sesión con tu correo institucional</p>
            </div>
          </div>
          <label className="block text-xs text-slate-400">
            Correo
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="nombre.apellido@cobgestion.cl"
              className={`${campo} mt-1`}
              required
            />
          </label>
          <label className="block text-xs text-slate-400">
            Clave
            <input
              type="password"
              autoComplete="current-password"
              value={clave}
              onChange={(e) => setClave(e.target.value)}
              className={`${campo} mt-1`}
              required
            />
          </label>
          {error && <p className="text-xs text-red-300">{error}</p>}
          <Boton variante="primario" className="w-full" disabled={cargando}>
            {cargando ? <Loader2 className="w-4 h-4 animate-spin" /> : <LogIn className="w-4 h-4" />} Ingresar
          </Boton>
          <p className="flex items-start gap-1.5 text-[11px] text-slate-500">
            <ShieldCheck className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            Cada acción queda registrada a tu nombre. Lo que puedes ver y hacer depende de tu cargo.
          </p>
        </form>

        {demo?.modo_demo && (
          <section className="md:col-span-3 bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4 text-xs">
            <div>
              <p className="font-semibold text-white text-sm">Cuentas del sandbox</p>
              <p className="text-slate-400">
                Entra con un clic para mostrar cada nivel. Clave de demostración:{' '}
                <code className="text-slate-200 bg-slate-800 px-1 rounded">{demo.clave}</code>
              </p>
            </div>
            {NIVELES.map(({ nivel, titulo, detalle }) => (
              <div key={nivel} className="space-y-1.5">
                <p className="text-slate-300 font-semibold">
                  {titulo} <span className="text-slate-500 font-normal">· {detalle}</span>
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  {demo.usuarios
                    ?.filter((u) => u.nivel === nivel)
                    .map((u) => (
                      <button
                        key={u.email}
                        type="button"
                        disabled={cargando}
                        onClick={() => entrar(u.email, demo.clave ?? '')}
                        className="text-left rounded-lg border border-slate-800 bg-slate-950/60 hover:border-indigo-500/60 hover:bg-slate-900 px-2.5 py-1.5 cursor-pointer disabled:opacity-50"
                      >
                        <p className="text-slate-100 font-medium truncate">{u.nombre}</p>
                        <p className="text-slate-500 truncate">{u.cargo}</p>
                      </button>
                    ))}
                </div>
              </div>
            ))}
          </section>
        )}
      </div>
    </div>
  );
};
