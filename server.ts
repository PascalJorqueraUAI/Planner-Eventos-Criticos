/**
 * API REST de Cobgestion.
 *
 * Expone el motor Python (capa Controlador + Modelo) a la interfaz React (capa Vista)
 * y a los sistemas actuales de Cobgestion (CRM, correo, planillas de mandantes).
 * Cada request se traduce en un comando de python_engine/cli.py; las llamadas se
 * encolan para que el repositorio nunca reciba dos escrituras simultáneas.
 *
 * Acceso: las personas inician sesión (cookie firmada, HttpOnly) y los sistemas externos
 * usan la clave de servicio COBGESTION_API_KEY (cabecera X-API-Key). El servidor solo
 * identifica a quién llama; qué puede hacer lo decide el motor (controlador/permisos.py).
 */
import express, { type Request, type Response } from 'express';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import { spawn } from 'child_process';
import { createHmac, randomBytes, timingSafeEqual } from 'crypto';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = Number(process.env.PORT) || 3000;
const INTERVALO_ESCANEO_MS = 60_000;
// Suficiente para un pantallazo re-codificado en el navegador (≤ 1600 px).
app.use(express.json({ limit: '8mb' }));

const pythonCommand = process.platform === 'win32' ? 'py' : 'python3';
const pythonArgs = process.platform === 'win32' ? ['-3'] : [];

class ErrorNegocio extends Error {}
class ErrorPermiso extends Error {}
class ErrorSesion extends Error {}

function ejecutarPython(comando: string, datos: Record<string, unknown> = {}): Promise<any> {
  return new Promise((resolve, reject) => {
    const proceso = spawn(pythonCommand, [...pythonArgs, 'python_engine/cli.py', comando], {
      cwd: process.cwd(),
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });
    // Se acumulan bytes y se decodifica al final: un carácter UTF-8 puede quedar partido entre dos chunks.
    const bytesSalida: Buffer[] = [];
    const bytesError: Buffer[] = [];
    proceso.stdout.on('data', (chunk: Buffer) => bytesSalida.push(chunk));
    proceso.stderr.on('data', (chunk: Buffer) => bytesError.push(chunk));
    proceso.on('error', reject);
    proceso.on('close', () => {
      const salida = Buffer.concat(bytesSalida).toString('utf8');
      const errores = Buffer.concat(bytesError).toString('utf8');
      try {
        const respuesta = JSON.parse(salida.trim());
        if (respuesta.ok) resolve(respuesta.datos);
        else reject(respuesta.prohibido ? new ErrorPermiso(respuesta.error) : new ErrorNegocio(respuesta.error));
      } catch {
        reject(new Error(errores || salida || 'El motor Python no devolvió JSON'));
      }
    });
    proceso.stdin.end(JSON.stringify(datos));
  });
}

// Cola: un comando a la vez sobre el repositorio.
let cola: Promise<unknown> = Promise.resolve();
function motor(comando: string, datos: Record<string, unknown> = {}): Promise<any> {
  const siguiente = cola.then(() => ejecutarPython(comando, datos));
  cola = siguiente.catch(() => undefined);
  return siguiente;
}

// ---------------- Sesiones ---------------- //
const COOKIE_SESION = 'cobgestion_sesion';
const DURACION_SESION_MS = 8 * 60 * 60 * 1000; // una jornada
// Sin SESSION_SECRET se genera uno al iniciar: reiniciar el servidor cierra todas las sesiones.
const SECRETO_SESION = process.env.SESSION_SECRET || randomBytes(32).toString('hex');
const CLAVE_INTEGRACION = process.env.COBGESTION_API_KEY || '';

const firmar = (contenido: string) => createHmac('sha256', SECRETO_SESION).update(contenido).digest('base64url');

function crearSesion(res: Response, usuarioId: string) {
  const contenido = Buffer.from(JSON.stringify({ uid: usuarioId, exp: Date.now() + DURACION_SESION_MS })).toString('base64url');
  res.setHeader(
    'Set-Cookie',
    `${COOKIE_SESION}=${contenido}.${firmar(contenido)}; HttpOnly; SameSite=Lax; Path=/; Max-Age=${DURACION_SESION_MS / 1000}`,
  );
}

function leerCookie(req: Request, nombre: string): string | undefined {
  const par = (req.headers.cookie ?? '').split(';').map((c) => c.trim()).find((c) => c.startsWith(`${nombre}=`));
  return par?.slice(nombre.length + 1);
}

const iguales = (a: string, b: string) => {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
};

/** Quién hace la solicitud: el id de usuario de la sesión, o "integracion" con la clave de servicio. */
function actor(req: Request): string {
  const clave = req.header('X-API-Key');
  if (clave && CLAVE_INTEGRACION && iguales(clave, CLAVE_INTEGRACION)) return 'integracion';
  const cookie = leerCookie(req, COOKIE_SESION);
  const [contenido, firma] = cookie?.split('.') ?? [];
  if (contenido && firma && iguales(firma, firmar(contenido))) {
    const { uid, exp } = JSON.parse(Buffer.from(contenido, 'base64url').toString('utf8'));
    if (typeof uid === 'string' && Date.now() < exp) return uid;
  }
  throw new ErrorSesion('Inicie sesión para continuar');
}

function ruta(handler: (req: Request, res: Response) => Promise<unknown>) {
  return async (req: Request, res: Response) => {
    try {
      res.json(await handler(req, res));
    } catch (err: any) {
      const estado = err instanceof ErrorSesion ? 401 : err instanceof ErrorPermiso ? 403 : err instanceof ErrorNegocio ? 400 : 500;
      res.status(estado).json({ error: err.message });
    }
  };
}

/** Comando del motor a nombre de quien llama. `usuario` solo lo usa una integración para decir qué sistema es. */
const comoActor = (req: Request, comando: string, datos: Record<string, unknown> = {}, sistema?: string) =>
  motor(comando, { ...datos, actor: actor(req), usuario: (req.body?.usuario as string) || sistema });

app.post(
  '/api/v1/sesion',
  ruta(async (req, res) => {
    const usuario = await motor('login', { email: req.body?.email, clave: req.body?.clave });
    crearSesion(res, usuario.id);
    return usuario;
  }),
);
app.get('/api/v1/sesion', ruta((req) => comoActor(req, 'sesion')));
app.delete(
  '/api/v1/sesion',
  ruta(async (_req, res) => {
    res.setHeader('Set-Cookie', `${COOKIE_SESION}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0`);
    return { ok: true };
  }),
);
// Cuentas del sandbox para entrar con un clic (solo en modo demo).
app.get('/api/v1/sesion/demo', ruta(() => motor('usuarios-demo')));

// ---------------- Repositorio centralizado ---------------- //
app.get('/api/v1/estado', ruta((req) => comoActor(req, 'estado')));
app.get('/api/v1/casos', ruta(async (req) => (await comoActor(req, 'estado')).casos));
app.get('/api/v1/casos/:id', ruta((req) => comoActor(req, 'caso', { caso_id: req.params.id })));

// Integración: el CRM informa un cambio en un caso (o una persona lo edita desde la interfaz).
app.patch(
  '/api/v1/casos/:id',
  ruta((req) => comoActor(req, 'actualizar-caso', { caso_id: req.params.id, cambios: req.body.cambios ?? req.body }, 'Integración CRM')),
);

// Integración: comprobante no estructurado ya extraído (WhatsApp, correo, aviso bancario).
app.post('/api/v1/avisos', ruta((req) => comoActor(req, 'ingresar-aviso', { aviso: req.body.aviso ?? req.body }, 'Ingesta de comprobantes')));

// Integración: planilla estructurada de un mandante.
app.post(
  '/api/v1/planillas-mandante',
  ruta((req) => comoActor(req, 'conciliar-planilla', { registros: req.body.registros }, 'Planilla mandante')),
);

// Un caso nuevo ingresado a mano (con comprobante inicial opcional): responde con sus eventos y asignaciones.
app.post(
  '/api/v1/casos',
  ruta((req) => comoActor(req, 'crear-caso', { caso: req.body.caso, comprobante: req.body.comprobante ?? null }, 'Ingreso manual de casos')),
);

// Integración: carga de casos desde un CSV del CRM o de una planilla (con validación previa opcional).
app.post(
  '/api/v1/importar-casos',
  ruta((req) =>
    comoActor(
      req,
      'importar-casos',
      { csv: req.body.csv, mapeo: req.body.mapeo, solo_validar: Boolean(req.body.solo_validar) },
      'Importación de casos',
    ),
  ),
);

app.post('/api/v1/exportar', ruta((req) => comoActor(req, 'exportar')));
app.post('/api/v1/reiniciar', ruta((req) => comoActor(req, 'reiniciar', { escenario: req.body?.escenario })));

// ---------------- Detector de eventos críticos ---------------- //
app.get('/api/v1/eventos', ruta(async (req) => (await comoActor(req, 'estado')).eventos));
app.post('/api/v1/detector/escanear', ruta((req) => comoActor(req, 'escanear')));

// ---------------- Asignación y seguimiento ---------------- //
app.get('/api/v1/tareas', ruta(async (req) => (await comoActor(req, 'estado')).tareas));
app.post(
  '/api/v1/tareas/:id/atender',
  ruta((req) =>
    comoActor(req, 'atender-tarea', { tarea_id: req.params.id, resultado: req.body.resultado, notas: req.body.notas ?? '' }),
  ),
);
app.post(
  '/api/v1/tareas/:id/reasignar',
  ruta((req) => comoActor(req, 'reasignar-tarea', { tarea_id: req.params.id, motivo: req.body.motivo ?? '' })),
);
app.get('/api/v1/colaboradores', ruta(async (req) => (await comoActor(req, 'estado')).colaboradores));
app.patch(
  '/api/v1/colaboradores/:id/disponibilidad',
  ruta((req) =>
    comoActor(req, 'disponibilidad', {
      colaborador_id: req.params.id,
      disponible: Boolean(req.body.disponible),
      motivo: req.body.motivo ?? '',
    }),
  ),
);

// Integración: RR.HH. o el CRM informan vacaciones, permisos o feriados de un colaborador.
app.post(
  '/api/v1/colaboradores/:id/ausencias',
  ruta((req) =>
    comoActor(
      req,
      'registrar-ausencia',
      { colaborador_id: req.params.id, desde: req.body.desde, hasta: req.body.hasta, motivo: req.body.motivo ?? '' },
      'Calendario RR.HH.',
    ),
  ),
);

// ---------------- Notificaciones ---------------- //
// Sin `ids` marca todas las del usuario como leídas.
app.post('/api/v1/notificaciones/leer', ruta((req) => comoActor(req, 'leer-notificaciones', { ids: req.body?.ids ?? null })));
app.get('/api/v1/correos', ruta(async (req) => (await comoActor(req, 'estado')).correos));

// ---------------- Dashboard de trazabilidad ---------------- //
app.get('/api/v1/metricas', ruta(async (req) => (await comoActor(req, 'estado')).metricas));

// ---------------- Extracción de comprobantes (complementaria al registro) ---------------- //
// Corre fuera de la cola: Gemini puede tardar segundos y la extracción solo lee el repositorio.
// El cuerpo de la solicitud (comprobante) nunca se registra en los logs.
app.post(
  '/api/v1/extraer-comprobante',
  ruta(async (req) => {
    const { texto, imagen_base64, mime_type, confirmacion_operador } = req.body;
    const quien = actor(req);
    const { datos, tratamiento } = await ejecutarPython('extraer-comprobante', {
      texto,
      imagen_base64,
      mime_type,
      confirmacion_operador,
      actor: quien,
    });
    if (tratamiento) await motor('registrar-tratamiento', { tratamiento, actor: quien });
    return datos;
  }),
);

// ---------------- Vista (Vite / estáticos) ---------------- //
async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({ server: { middlewareMode: true }, appType: 'spa' });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.resolve('dist')));
    app.get('*', (_req, res) => res.sendFile(path.resolve('dist/index.html')));
  }

  // El detector compara constantemente el estado de los casos contra el catálogo.
  setInterval(() => {
    motor('escanear').catch((err) => console.error('Escaneo periódico falló:', err.message));
  }, INTERVALO_ESCANEO_MS);

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Cobgestion API REST en http://localhost:${PORT}/api/v1`);
  });
}

startServer();
