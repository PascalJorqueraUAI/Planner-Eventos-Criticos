/**
 * API REST de Cobgestion.
 *
 * Expone el motor Python (capa Controlador + Modelo) a la interfaz React (capa Vista)
 * y a los sistemas actuales de Cobgestion (CRM, correo, planillas de mandantes).
 * Cada request se traduce en un comando de python_engine/cli.py; las llamadas se
 * encolan para que el repositorio nunca reciba dos escrituras simultáneas.
 */
import express, { type Request, type Response } from 'express';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import { spawn } from 'child_process';
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
        else reject(new ErrorNegocio(respuesta.error));
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

function ruta(handler: (req: Request) => Promise<unknown>) {
  return async (req: Request, res: Response) => {
    try {
      res.json(await handler(req));
    } catch (err: any) {
      res.status(err instanceof ErrorNegocio ? 400 : 500).json({ error: err.message });
    }
  };
}

const usuario = (req: Request, porDefecto: string) =>
  (req.body?.usuario as string) || (req.header('X-Usuario') as string) || porDefecto;

// ---------------- Repositorio centralizado ---------------- //
app.get('/api/v1/estado', ruta(() => motor('estado')));
app.get('/api/v1/casos', ruta(async () => (await motor('estado')).casos));
app.get('/api/v1/casos/:id', ruta((req) => motor('caso', { caso_id: req.params.id })));

// Integración: el CRM informa un cambio en un caso.
app.patch(
  '/api/v1/casos/:id',
  ruta((req) =>
    motor('actualizar-caso', {
      caso_id: req.params.id,
      cambios: req.body.cambios ?? req.body,
      usuario: usuario(req, 'Integración CRM'),
    }),
  ),
);

// Integración: comprobante no estructurado ya extraído (WhatsApp, correo, aviso bancario).
app.post(
  '/api/v1/avisos',
  ruta((req) => motor('ingresar-aviso', { aviso: req.body.aviso ?? req.body, usuario: usuario(req, 'Ingesta de comprobantes') })),
);

// Integración: planilla estructurada de un mandante.
app.post(
  '/api/v1/planillas-mandante',
  ruta((req) => motor('conciliar-planilla', { registros: req.body.registros, usuario: usuario(req, 'Planilla mandante') })),
);

// Un caso nuevo ingresado a mano (con comprobante inicial opcional): responde con sus eventos y asignaciones.
app.post(
  '/api/v1/casos',
  ruta((req) =>
    motor('crear-caso', {
      caso: req.body.caso,
      comprobante: req.body.comprobante ?? null,
      usuario: usuario(req, 'Ingreso manual de casos'),
    }),
  ),
);

// Integración: carga de casos desde un CSV del CRM o de una planilla (con validación previa opcional).
app.post(
  '/api/v1/importar-casos',
  ruta((req) =>
    motor('importar-casos', {
      csv: req.body.csv,
      mapeo: req.body.mapeo,
      solo_validar: Boolean(req.body.solo_validar),
      usuario: usuario(req, 'Importación de casos'),
    }),
  ),
);

app.post('/api/v1/exportar', ruta(() => motor('exportar')));
app.post('/api/v1/reiniciar', ruta((req) => motor('reiniciar', { escenario: req.body?.escenario })));

// ---------------- Detector de eventos críticos ---------------- //
app.get('/api/v1/eventos', ruta(async () => (await motor('estado')).eventos));
app.post('/api/v1/detector/escanear', ruta(() => motor('escanear')));

// ---------------- Asignación y seguimiento ---------------- //
app.get('/api/v1/tareas', ruta(async () => (await motor('estado')).tareas));
app.post(
  '/api/v1/tareas/:id/atender',
  ruta((req) =>
    motor('atender-tarea', {
      tarea_id: req.params.id,
      resultado: req.body.resultado,
      notas: req.body.notas ?? '',
      usuario: usuario(req, 'Responsable'),
    }),
  ),
);
app.post(
  '/api/v1/tareas/:id/reasignar',
  ruta((req) =>
    motor('reasignar-tarea', { tarea_id: req.params.id, motivo: req.body.motivo ?? '', usuario: usuario(req, 'Jefatura') }),
  ),
);
app.get('/api/v1/colaboradores', ruta(async () => (await motor('estado')).colaboradores));
app.patch(
  '/api/v1/colaboradores/:id/disponibilidad',
  ruta((req) =>
    motor('disponibilidad', {
      colaborador_id: req.params.id,
      disponible: Boolean(req.body.disponible),
      motivo: req.body.motivo ?? '',
      usuario: usuario(req, 'Jefatura'),
    }),
  ),
);

// Integración: RR.HH. o el CRM informan vacaciones, permisos o feriados de un colaborador.
app.post(
  '/api/v1/colaboradores/:id/ausencias',
  ruta((req) =>
    motor('registrar-ausencia', {
      colaborador_id: req.params.id,
      desde: req.body.desde,
      hasta: req.body.hasta,
      motivo: req.body.motivo ?? '',
      usuario: usuario(req, 'Calendario RR.HH.'),
    }),
  ),
);

// ---------------- Dashboard de trazabilidad ---------------- //
app.get('/api/v1/metricas', ruta(async () => (await motor('estado')).metricas));

// ---------------- Extracción de comprobantes (complementaria al registro) ---------------- //
// Corre fuera de la cola: Gemini puede tardar segundos y la extracción solo lee el repositorio.
// El cuerpo de la solicitud (comprobante) nunca se registra en los logs.
app.post(
  '/api/v1/extraer-comprobante',
  ruta(async (req) => {
    const { texto, imagen_base64, mime_type, confirmacion_operador } = req.body;
    const { datos, tratamiento } = await ejecutarPython('extraer-comprobante', {
      texto,
      imagen_base64,
      mime_type,
      confirmacion_operador,
      usuario: usuario(req, 'Operador de ingesta'),
    });
    if (tratamiento) await motor('registrar-tratamiento', { tratamiento });
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
