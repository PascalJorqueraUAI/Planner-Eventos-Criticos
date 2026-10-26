# Cobgestion · Sistema Integrado de Eventos Críticos

Prototipo para **Cobgestion**, empresa LegalTech de cobranza judicial y extrajudicial, que reduce los desfases de información entre el **Área Comercial** (análisis de datos y gestión de cobranza) y el **Área Judicial** (gestión de causas y recuperación de acreencias).

> **¿Primera vez?** Ve directo a la [Guía para el equipo](#guía-para-el-equipo-correr-el-sistema).

## Problema

Cobgestion trabaja con un sistema híbrido de CRM y planillas. Los pagos quedan en planillas comerciales sin conciliar y se cruzan cada cierto tiempo contra las planillas de los mandantes. Además, muchos pagos llegan como **datos no estructurados**: pantallazos que los clientes envían por correo o WhatsApp, o correos automáticos del banco.

> **Caso real.** Un viernes llegó un comprobante de pago. Por el feriado del lunes, la ejecutiva lo vio el martes y tampoco se procesó a tiempo. Judicial no sabía del pago, la causa siguió y **se incautó el vehículo del deudor**. Cobgestion asumió las costas y devolvió el auto: unos **$600.000 CLP** perdidos por un error de coordinación.

**Evento crítico:** un cambio o antecedente relevante de un caso que requiere que otra área revise su gestión, tome una decisión o actúe dentro de un plazo definido. Incluye un comprobante que todavía está pendiente de verificación.

## Los 4 módulos

| # | Módulo | Qué hace | Dónde vive |
|---|---|---|---|
| 1 | **Repositorio centralizado** | Planilla única con el estado actual de cada caso, sus avisos de pago, la última actualización y el historial de cambios (campo, valor anterior, valor nuevo, quién y cuándo). Recibe datos del CRM, de los comprobantes no estructurados y de las planillas de mandantes. Exporta a Excel. | `modelo/repositorio.py`, `RepositorioView.tsx` |
| 2 | **Detector de eventos críticos** | Compara el estado de todos los casos contra un **catálogo de eventos** (cada minuto y después de cada cambio) y crea el evento y sus tareas paralelas cuando una regla se cumple. | `controlador/catalogo_eventos.py`, `controlador/detector.py`, `DetectorView.tsx` |
| 3 | **Asignación y seguimiento** | Asigna cada tarea con una **matriz RACI** y un **modelo de asignación óptima** (método húngaro) según el historial, la disponibilidad y la carga de los colaboradores. La tarea queda *Pendiente* hasta que se marca *Atendida*. | `controlador/asignador.py`, `controlador/seguimiento.py`, `AsignacionView.tsx` |
| 4 | **Dashboard de trazabilidad** | Estado real de los casos y métricas de desempeño: SLA, tareas vencidas, desfase aviso→alerta, carga por colaborador, riesgo expuesto y cubierto, y registro de auditoría. | `controlador/trazabilidad.py`, `DashboardView.tsx` |

### Catálogo de eventos críticos

| Código | Evento | Condición | Tareas paralelas |
|---|---|---|---|
| EC-01 | Pago informado pendiente de verificación | Aviso en estado *informado* | Comercial verifica el pago · Judicial evalúa suspender apremios |
| EC-02 | Pago observado con diferencias | Aviso en estado *observado* | Comercial aclara la diferencia · Judicial evalúa el curso de la causa |
| EC-03 | Pago confirmado con causa activa | Aviso *confirmado*, causa no suspendida formalmente ni terminada | Judicial presenta la suspensión formal o el término · Comercial registra el pago en el CRM |
| EC-04 | Diligencia inminente con negociación abierta | Apremio en curso, diligencia en ≤ 72 h y negociación vigente | Judicial confirma o reprograma con el receptor · Comercial contacta al deudor |
| EC-05 | Convenio incumplido con causa suspendida | Convenio incumplido y causa suspendida | Judicial evalúa reactivar · Comercial intenta repactar |

Si la causa tiene un **apremio en curso** (embargo, orden de incautación o receptor programado), el evento sube a **CRÍTICO**, se marca un riesgo de $600.000 y el SLA judicial baja a **4 horas**. Desde el estado *informado* se alerta a Judicial: no se espera la conciliación.

**Cierre coordinado:** un evento solo se cierra cuando **todas** sus tareas están atendidas. Que Comercial confirme el pago no cierra el evento si Judicial aún no suspendió la diligencia.

### Modelo de asignación (RACI + investigación de operaciones)

1. **Matriz RACI por tipo de tarea.** Define qué cargo es **R**esponsable de ejecutarla, quién **A**prueba y recibe escalamientos (jefatura), a quién se **C**onsulta y a quién se **I**nforma.
2. **Problema de asignación.** Entre los colaboradores con el cargo R:

   ```
   max  Σ puntaje(c, t) · x(c, t)
   s.a. cada tarea tiene exactamente un responsable
        Σ_t x(c, t) ≤ capacidad libre de c
        x(c, t) = 0 si c no está disponible, no tiene la competencia o no tiene el cargo R

   puntaje = w_exp·experiencia + w_des·desempeño + w_disp·disponibilidad + w_cont·continuidad
     experiencia    = n / (n + 5)              n = tareas de ese tipo ya atendidas
     desempeño      = (cumplidas_SLA + 1) / (n + 2)
     disponibilidad = 1 − carga / capacidad    carga = tareas del CRM + pendientes del sistema
     continuidad    = 1 si es el titular del caso
   ```

   Pesos normales: 30 / 25 / 30 / 15. En tareas **críticas** pesa más que alguien la tome ya y la cumpla a tiempo: 20 / 30 / 40 / 10.
3. Se resuelve con el **método húngaro** sobre todas las tareas nuevas a la vez (matriz tareas × cupos de capacidad). Si no hay nadie factible, la tarea **se escala** a la jefatura (A).
4. Cada tarea atendida alimenta el historial de su responsable.

**Qué es automático y qué es manual.** El sistema no espera a que un jefe reparta el trabajo. En cada ciclo del detector (cada minuto y después de cada cambio):

| Automatismo | Qué hace |
|---|---|
| Asignación | Toda tarea nueva recibe responsable y RACI en el momento en que se detecta el evento. |
| Calendario de ausencias | Las ausencias se programan con anticipación (desde la interfaz o vía `POST /api/v1/colaboradores/:id/ausencias`, pensado para RR.HH. o el CRM). Al empezar, el colaborador queda no disponible y sus tareas se reasignan; al terminar, vuelve solo. |
| Ausencias futuras | No se asigna una tarea a quien se ausentará antes de su vencimiento. Al programar una ausencia, las tareas que vencen dentro de ella se reasignan de inmediato. |
| Escalamiento por vencimiento | Una tarea que vence se reasigna al mejor colaborador alternativo con la mitad del SLA como plazo, y el incumplimiento queda en el historial del responsable original. Si también vence ese plazo, pasa a la jefatura (A). |

Lo único manual es **marcar la tarea como atendida** con su resultado. Reasignar a pedido o marcar una ausencia imprevista quedan como excepciones. En el sandbox, la titular comercial del caso del auto tiene un permiso en el calendario: el sistema la marca no disponible solo y asigna el comprobante a otra persona.

La interfaz muestra, para cada tarea, el ranking de candidatos, el puntaje por criterio y el motivo por el que cada persona quedó excluida.

## Extracción de comprobantes y protección de datos personales

La extracción con IA es **complementaria al registro**: solo prellena el formulario. El comprobante siempre se puede registrar a mano, y nada se registra sin que una persona revise los datos. El diseño considera la Ley 19.628, hoy vigente, y la Ley 21.719, que entra en vigencia el 1 de diciembre de 2026.

| Principio | Cómo se aplica (`python_engine/controlador/extraccion.py`) |
|---|---|
| Proporcionalidad | Primero se extrae localmente. Gemini solo se usa con una imagen o si el texto no alcanzó para obtener monto, RUT y N° de operación. |
| Minimización / seudonimización | Antes de enviar texto, RUT, correos, teléfonos, números de cuenta y nombres de deudores conocidos se reemplazan por marcadores (`[RUT_1]`). La respuesta se reidentifica en el servidor. El operador puede ver exactamente qué texto salió. |
| Imágenes | Se recodifican en el navegador, sin metadatos EXIF/GPS y a un máximo de 1600 px. Como no se pueden seudonimizar, el operador confirma cada envío. Nunca se almacenan: solo su hash SHA-256. |
| Licitud y transferencia internacional | Gemini permanece apagado hasta que `GEMINI_TRATAMIENTO_AUTORIZADO=si`. Ver la lista de requisitos más abajo. |
| Responsabilidad | Cada envío queda en el **registro de tratamientos** (operador, fecha, finalidad, proveedor, ubicación, categorías de datos, medidas y hash, sin el contenido). Se ve en el Dashboard y se exporta a Excel. |
| Supervisión humana | Los datos extraídos son editables. Lo que se lee localmente prevalece sobre lo que interpreta el tercero. |

**Antes de activar Gemini** (`GEMINI_TRATAMIENTO_AUTORIZADO=si`), Cobgestion debe:

1. Activar la facturación en el proyecto de Google Cloud. En el plan gratuito, Google puede usar los datos para mejorar sus productos y personas pueden revisarlos. En el plan pagado, no los usa para entrenar y actúa como encargado del tratamiento.
2. Aceptar el anexo de procesamiento de datos (DPA) de Google.
3. Definir la base legal de la transferencia internacional (por ejemplo, cláusulas contractuales modelo).
4. Informar este tratamiento en su política de privacidad y en su registro de actividades.

Esto requiere validación legal: el sistema aporta las medidas técnicas, no reemplaza esa revisión.

## Arquitectura

**Modelo-Vista-Controlador (MVC):**

```
python_engine/
├── modelo/                    MODELO: datos y acceso al repositorio
│   ├── entidades.py           Esquema de cada hoja (Caso, AvisoPago, EventoCritico, Tarea, Colaborador…)
│   ├── repositorio.py         Persistencia JSON, historial de cambios, exportación CSV
│   └── datos_iniciales.py     Datos del sandbox (casos, colaboradores e historial de desempeño)
├── controlador/               CONTROLADOR: reglas de negocio
│   ├── catalogo_eventos.py    Catálogo declarativo de eventos críticos
│   ├── detector.py            Detector de eventos (idempotente)
│   ├── asignador.py           Matriz RACI + método húngaro
│   ├── seguimiento.py         Atender, cierre coordinado, calendario de ausencias, escalamiento
│   ├── conciliador.py         Planillas estructuradas de mandantes
│   ├── extraccion.py          Extracción local + Gemini con seudonimización y registro de tratamientos
│   ├── trazabilidad.py        Métricas del dashboard
│   └── servicio.py            Casos de uso; cada cambio dispara un ciclo de detección
├── tests/                     Pruebas unitarias por componente (unittest)
└── cli.py                     Punto de entrada: comando + JSON por stdin → JSON por stdout
server.ts                      API REST /api/v1 (Express)
src/                           VISTA: React + Tailwind (una vista por módulo)
```

### API REST (integración con los sistemas de Cobgestion)

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/v1/estado` | Estado completo para la Vista |
| GET | `/api/v1/casos`, `/api/v1/casos/:id` | Casos (con avisos, eventos, tareas e historial) |
| PATCH | `/api/v1/casos/:id` | **El CRM informa un cambio en un caso** (estado comercial/judicial, fecha de diligencia, titulares) |
| POST | `/api/v1/avisos` | Comprobante no estructurado ya extraído; se asocia por `caso_id` o por RUT |
| POST | `/api/v1/planillas-mandante` | Planilla estructurada de un mandante |
| POST | `/api/v1/extraer-comprobante` | `{ texto, imagen_base64?, confirmacion_operador? }`: prellena monto, RUT y N° de operación (local o Gemini, con los resguardos descritos) |
| GET / POST | `/api/v1/eventos`, `/api/v1/detector/escanear` | Eventos y escaneo manual |
| GET | `/api/v1/tareas` | Tareas con indicador de vencimiento |
| POST | `/api/v1/tareas/:id/atender` | `{ resultado, notas }`: marca la tarea como atendida |
| POST | `/api/v1/tareas/:id/reasignar` | Reasigna excluyendo al responsable actual |
| PATCH | `/api/v1/colaboradores/:id/disponibilidad` | `{ disponible, motivo }`: cambio manual; reasigna las pendientes |
| POST | `/api/v1/colaboradores/:id/ausencias` | `{ desde, hasta, motivo }`: ausencia programada (RR.HH. / CRM) |
| GET | `/api/v1/metricas` | Métricas del dashboard |
| POST | `/api/v1/exportar` · `/api/v1/reiniciar` | Exportar a CSV · recargar el sandbox |

Ejemplo, el CRM avisa que una causa tiene orden de incautación con diligencia mañana:

```bash
curl -X PATCH http://localhost:3000/api/v1/casos/CASO-1055 \
  -H "Content-Type: application/json" \
  -d '{"cambios": {"estado_judicial": "Orden de incautación vigente", "estado_comercial": "En negociación", "fecha_diligencia": "2026-10-27T10:00:00"}}'
```

La respuesta incluye `deteccion.eventos_nuevos` con el evento EC-04 ya creado y asignado.

## Guía para el equipo: correr el sistema

### 1. Requisitos

| Herramienta | Versión | Cómo verificar |
|---|---|---|
| Node.js | 20.19 o superior | `node --version` |
| Python | 3.10 o superior (solo biblioteca estándar, sin `pip install`) | Windows: `py -3 --version` · macOS/Linux: `python3 --version` |
| Git | cualquiera reciente | `git --version` |

### 2. Instalar

```bash
git clone <URL_DEL_REPOSITORIO>
cd Planner-Eventos-Criticos
git checkout refactor/cuatro-modulos-mvc   # mientras no esté fusionada en main
npm install
```

### 3. Configurar el `.env`

```bash
cp .env.example .env      # en PowerShell: Copy-Item .env.example .env
```

El sistema funciona **sin clave de Gemini**: la extracción de comprobantes queda solo local y los datos se completan a mano. Para usar Gemini:

1. Cada integrante crea **su propia** clave en [Google AI Studio](https://aistudio.google.com/apikey) y la pega en `GEMINI_API_KEY`. **Nunca subas el `.env` ni compartas la clave por el chat del grupo**: el `.gitignore` ya lo excluye.
2. Guarda el archivo y comprueba que la clave y el modelo funcionan: `npm run test:gemini`.
3. Para que la interfaz use Gemini, cambia `GEMINI_TRATAMIENTO_AUTORIZADO="si"`. Hazlo **solo con datos de prueba**. Con datos reales de deudores, antes hay que cumplir los requisitos de la sección [Extracción de comprobantes y protección de datos personales](#extracción-de-comprobantes-y-protección-de-datos-personales).

### 4. Levantar la aplicación

```bash
npm run dev
```

Abre <http://localhost:3000>. La primera vez se crea `python_engine/data_store.json` con los datos del sandbox (no se versiona). El botón **Reiniciar sandbox** vuelve al estado inicial.

En Windows, ejecuta los comandos desde **PowerShell** o la terminal de VS Code, no desde Git Bash (ver problemas frecuentes).

### 5. Recorrido sugerido para la demo

1. **Repositorio:** abre CASO-1052 (el auto Suzuki) y revisa su historial de cambios.
2. **Detector:** hay 5 eventos detectados al cargar el sandbox. EC-01 es el comprobante del auto, con prioridad crítica y SLA judicial de 4 h.
3. **Asignación:** en "¿Por qué esta persona?" se ve que Camila, titular del caso, quedó excluida por su permiso en el calendario. Programa una ausencia a otro colaborador y mira cómo se reasignan sus tareas.
4. **Cierre coordinado:** marca como atendida la tarea comercial ("Pago confirmado"). El evento sigue abierto hasta que Judicial atienda la suya.
5. **Repositorio → Registrar comprobante:** registra el correo del camión KR-WP-19. El detector crea el evento en el acto.
6. **Trazabilidad:** métricas, carga por colaborador, auditoría y registro de tratamientos de datos.

### 6. Pruebas

| Comando | Qué hace | Red |
|---|---|---|
| `npm test` | Pruebas unitarias del motor Python (detector, asignación, seguimiento, extracción, privacidad) | No |
| `npm run lint` | Chequeo de tipos de la Vista y la API | No |
| `npm run test:gemini` | Integración **real** con Gemini usando solo datos ficticios (texto y `tests/fixtures/comprobante_ficticio.png`). Se omite si no hay clave. | Sí, consume cuota |

### 7. Uso del motor sin la interfaz

```bash
py -3 python_engine/cli.py estado       # macOS/Linux: python3 python_engine/cli.py estado
py -3 python_engine/cli.py escanear
py -3 python_engine/cli.py exportar     # CSV para Excel en ./exports
py -3 python_engine/cli.py reiniciar
```

### Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `spawn py ENOENT` o "no se encontró py" | En Windows, Git Bash no ve el lanzador `py`. Usa PowerShell. Si tampoco funciona ahí, instala Python desde python.org marcando "py launcher". |
| `EADDRINUSE ... 3000` | Ya hay otra instancia corriendo. Ciérrala (Ctrl+C en su terminal) o cambia `PORT` en el `.env`. |
| La interfaz falla tras actualizar el código | El `data_store.json` quedó con un formato anterior. Presiona **Reiniciar sandbox** o borra `python_engine/data_store.json`. |
| `npm run test:gemini` dice "skipped" | No hay clave en el `.env`, o el archivo no se guardó. |
| `npm run test:gemini` falla con HTTP 404 en el modelo | El modelo de `GEMINI_MODEL` no está disponible para tu clave: revisa los nombres vigentes en la [documentación de modelos](https://ai.google.dev/gemini-api/docs/models). |
| Gemini responde 429 | Se acabó la cuota del plan. Espera o revisa la facturación del proyecto. |

## Estados de pago

| Estado | Significado | Evento que dispara |
|---|---|---|
| **Informado / por confirmar** | Llegó el aviso o comprobante; falta verificarlo | EC-01: alerta judicial inmediata |
| **Confirmado** | Verificado contra la cartola o la planilla del mandante | EC-03 si la causa sigue activa |
| **Observado / no confirmado** | Diferencias o antecedentes pendientes | EC-02 |

## Licencia

Apache-2.0.
