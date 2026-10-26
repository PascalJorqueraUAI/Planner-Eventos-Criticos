// Ejecuta Python 3 con el comando correcto según el sistema operativo
// (Windows: `py -3`; macOS/Linux: `python3`), igual que server.ts.
// Uso: node scripts/python.mjs <argumentos de python...>
import { spawnSync } from 'node:child_process';

const [comando, ...base] = process.platform === 'win32' ? ['py', '-3'] : ['python3'];
const resultado = spawnSync(comando, [...base, ...process.argv.slice(2)], { stdio: 'inherit' });
if (resultado.error) {
  console.error(`No se pudo ejecutar "${comando}". ¿Está instalado Python 3.10 o superior?`);
  process.exit(1);
}
process.exit(resultado.status ?? 1);
