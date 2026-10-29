# Cobgestion · Sistema Integrado de Eventos Críticos

Prototipo para **Cobgestion**, empresa LegalTech de cobranza judicial y extrajudicial, que reduce los desfases de información entre el **Área Comercial** (análisis de datos y gestión de cobranza) y el **Área Judicial** (gestión de causas y recuperación de acreencias).

> **¿Primera vez?** Ve directo a la [Guía para el equipo](#guía-para-el-equipo-correr-el-sistema).
> **¿Vas a instalarlo en Cobgestion?** Sigue [docs/puesta_en_marcha.md](docs/puesta_en_marcha.md).

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

Si la causa tiene un **apremio en curso** (embargo, orden de incautación o receptor programado), el evento sube a **CRÍTICO** y el SLA judicial baja a **4 horas**. Desde el estado *informado* se alerta a Judicial: no se espera la conciliación.

**Riesgo de cada evento.** Es lo que Cobgestion asumiría si el apremio sigue sin que Judicial actúe. Se estima con el contexto del caso ([riesgo.py](python_engine/controlador/riesgo.py)) y la interfaz muestra el desglose:

| Contexto | Qué suma |
|---|---|
| Orden de incautación o diligencia con receptor sobre un bien que se retira | Receptor + retiro (grúa, grúa cama baja para camiones y maquinaria, flete para muebles) + 15 días de custodia + devolución |
| Mandamiento de embargo, o inmueble | Receptor + anotación y alzamiento en el RVM (vehículos) o el CBR (inmuebles) |
| Siempre | Costas personales: 3 % de la deuda (mínimo $50.000, máximo $600.000) |

> ⚠️ Las tarifas son **supuestos de la demo**, calibrados para que el caso del auto (CASO-1052) dé ≈ $600.000, el costo real de la incautación. Antes de presentar cifras como reales, reemplázalas por los costos efectivos de Cobgestion: están todas al inicio de `riesgo.py`.

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
│   ├── importador.py          Carga de casos desde CSV del CRM o planillas, con validación
│   ├── conciliador.py         Planillas estructuradas de mandantes
│   ├── extraccion.py          Extracción local + Gemini con seudonimización y registro de tratamientos
│   ├── trazabilidad.py        Métricas del dashboard
│   └── servicio.py            Casos de uso; cada cambio dispara un ciclo de detección
├── tests/                     Pruebas unitarias por componente (unittest)
├── cli.py                     Punto de entrada: comando + JSON por stdin → JSON por stdout
├── evidencia.py               Paquete de evidencia: detección, recorrido, simulación y pruebas
└── importar_casos.py          Carga de casos desde un CSV por línea de comandos
docs/                          Guía de puesta en marcha, plantilla de carga y mapeo de columnas
server.ts                      API REST /api/v1 (Express)
src/                           VISTA: React + Tailwind (una vista por módulo)
```

### API REST (integración con los sistemas de Cobgestion)

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/v1/estado` | Estado completo para la Vista |
| GET | `/api/v1/casos`, `/api/v1/casos/:id` | Casos (con avisos, eventos, tareas e historial) |
| POST | `/api/v1/casos` | `{ caso, comprobante? }`: crea un caso con las mismas validaciones del importador, y opcionalmente su primer comprobante. Responde con los eventos detectados y la asignación de cada tarea |
| PATCH | `/api/v1/casos/:id` | **El CRM informa un cambio en un caso** (estado comercial/judicial, fecha de diligencia, titulares) |
| POST | `/api/v1/avisos` | Comprobante no estructurado ya extraído; se asocia por `caso_id` o por RUT |
| POST | `/api/v1/planillas-mandante` | Planilla estructurada de un mandante |
| POST | `/api/v1/importar-casos` | `{ csv, mapeo?, solo_validar? }`: carga casos desde una exportación del CRM o una planilla (ver [Importación de casos](#importación-de-casos-desde-el-crm-o-una-planilla)) |
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
npm install
```

### 3. Configurar el `.env`

```bash
cp .env.example .env      # en PowerShell: Copy-Item .env.example .env
```

El sistema funciona **sin clave de Gemini**: la extracción de comprobantes queda solo local y los datos se completan a mano. Para usar Gemini:

1. Cada integrante crea **su propia** clave en [Google AI Studio](https://aistudio.google.com/apikey) y la pega en `GEMINI_API_KEY`. **Nunca subas el `.env` ni compartas la clave por el chat del grupo**: el `.gitignore` ya lo excluye.
2. Pon `GEMINI_TRATAMIENTO_AUTORIZADO="si"` para que la interfaz use Gemini.
3. **Guarda el archivo y reinicia `npm run dev`** (Ctrl+C y de nuevo). El servidor lee el `.env` solo al arrancar.
4. Comprueba que funciona con `npm run test:gemini`.
5. En la interfaz, *Registrar comprobante* debe mostrar "Gemini habilitado" con el modelo en uso.

Configuración verificada con llamadas reales (26-10-2026): `GEMINI_MODEL="gemini-3.6-flash"` y `GEMINI_THINKING_LEVEL="minimal"`. Con imágenes de comprobantes respondió entre 5 y 30 s según la demanda. Si Google devuelve 503 o se demora, el sistema reintenta solo hasta por unos 100 s.

> ⚠️ **Plan gratuito: solo datos ficticios.** Una clave nueva de AI Studio queda en el plan gratuito, salvo que el proyecto tenga facturación activa. En ese plan:
> - **Google puede usar lo que envías para entrenar sus modelos**, y personas pueden revisarlo. Úsalo solo con los datos inventados del sandbox. Con datos reales de deudores hay que cumplir los requisitos de la sección [Extracción de comprobantes y protección de datos personales](#extracción-de-comprobantes-y-protección-de-datos-personales).
> - **El límite es de 20 extracciones al día por modelo** (sin contar las extracciones locales). `npm run test:gemini` gasta 2. **El día de la presentación no corran pruebas de más.** Si se agota, la interfaz lo avisa ("cuota diaria del plan gratuito agotada; se renueva en…") y sigue funcionando con la extracción local.

### 4. Levantar la aplicación

```bash
npm run dev
```

Abre <http://localhost:3000>. La primera vez se crea `python_engine/data_store.json` con los datos del sandbox (no se versiona). El botón **Reiniciar sandbox** vuelve al estado inicial.

En Windows, ejecuta los comandos desde **PowerShell** o la terminal de VS Code, no desde Git Bash (ver problemas frecuentes).

### 5. Recorrido sugerido para la demo

1. **Repositorio:** abre CASO-1052 (el auto Suzuki) y revisa su historial de cambios.
2. **Detector:** hay 16 eventos detectados al cargar el sandbox ampliado (24 casos, 14 colaboradores). EC-01 del CASO-1052 es el comprobante del auto, con prioridad crítica y SLA judicial de 4 h.
3. **Asignación:** en "¿Por qué esta persona?" se ve que Camila, titular del caso, quedó excluida por su permiso en el calendario. Programa una ausencia a otro colaborador y mira cómo se reasignan sus tareas.
4. **Cierre coordinado:** marca como atendida la tarea comercial ("Pago confirmado"). El evento sigue abierto hasta que Judicial atienda la suya.
5. **Repositorio → Nuevo caso:** elige el ejemplo "Auto con incautación + comprobante" y presiona *Crear caso y ejecutar detector*. El formulario muestra en el acto:
   - el evento detectado (EC-01 crítico);
   - a quién se asignó cada tarea y con qué puntaje;
   - los demás candidatos;
   - por qué se excluyó a cada colaborador (permiso, licencia, sin capacidad).

   Con "Caso sin riesgo (control)" se ve que no todo caso genera alertas. Si eliges como titular a alguien marcado "(no disponible)", el sistema asigna la tarea a otra persona.
6. **Repositorio → Registrar comprobante:** registra el correo del camión KR-WP-19. El detector crea el evento en el acto.
7. **Gemini (si está habilitado):** en *Registrar comprobante → Imagen*, sube `python_engine/tests/fixtures/comprobante_ficticio.png`, confirma el envío y presiona *Extraer datos*. Se prellenan monto, RUT y N° de operación. Con el ejemplo "WhatsApp sin N° de operación", despliega "Ver exactamente qué texto salió hacia Gemini" para mostrar la seudonimización (`[RUT_1]`, `[CORREO_1]`…).
8. **Trazabilidad:** métricas, carga por colaborador, auditoría y el registro de tratamientos, donde queda cada envío a Gemini.

### 6. Pruebas

| Comando | Qué hace | Red |
|---|---|---|
| `npm test` | Pruebas unitarias del motor Python (detector, riesgo, asignación, seguimiento, ingreso e importación de casos, extracción, privacidad, evidencia) | No |
| `npm run lint` | Chequeo de tipos de la Vista y la API | No |
| `npm run evidencia` | Genera `evidencia/<fecha>/` con el resumen para la presentación: detección caso por caso, recorrido de la demo, simulación de una semana, pruebas y exportaciones CSV (ver [Paquete de evidencia](#paquete-de-evidencia)) | No |
| `npm run test:gemini` | Integración **real** con Gemini usando solo datos ficticios (texto y `tests/fixtures/comprobante_ficticio.png`). Se omite si no hay clave o si la cuota está agotada. | Sí, gasta 2 de las 20 solicitudes diarias |

### 7. Uso del motor sin la interfaz

```bash
py -3 python_engine/cli.py estado       # macOS/Linux: python3 python_engine/cli.py estado
py -3 python_engine/cli.py escanear
py -3 python_engine/cli.py exportar     # CSV para Excel en ./exports
py -3 python_engine/cli.py reiniciar
py -3 python_engine/evidencia.py       # paquete de evidencia (--dias N, --sin-pruebas, --salida carpeta)
py -3 python_engine/importar_casos.py casos.csv --validar
```

### Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `spawn py ENOENT` o "no se encontró py" | En Windows, Git Bash no ve el lanzador `py`. Usa PowerShell. Si tampoco funciona ahí, instala Python desde python.org marcando "py launcher". |
| `EADDRINUSE ... 3000` | Ya hay otra instancia corriendo. Ciérrala (Ctrl+C en su terminal) o cambia `PORT` en el `.env`. |
| La interfaz falla tras actualizar el código | El `data_store.json` quedó con un formato anterior. Presiona **Reiniciar sandbox** o borra `python_engine/data_store.json`. |
| Todos los eventos críticos muestran un riesgo de $600.000 | Son eventos detectados antes de que el riesgo se calculara según cada caso, y no se recalculan solos. Reinicia `npm run dev` y presiona **Reiniciar sandbox**. |
| La interfaz dice "falta GEMINI_TRATAMIENTO_AUTORIZADO=si" aunque ya lo pusiste | El servidor se inició antes del cambio. Reinicia `npm run dev`. |
| `npm run test:gemini` dice "skipped" | Sin clave: no hay clave en el `.env` o no se guardó. Con el motivo "cuota … agotada": se acabaron las 20 solicitudes diarias del plan gratuito (ver el punto siguiente). |
| "cuota diaria del plan gratuito de Gemini agotada" | Espera el tiempo indicado, usa la clave de otro integrante o cambia a otro modelo, que tiene cuota propia (por ejemplo `GEMINI_MODEL="gemini-3.5-flash-lite"`). Mientras tanto, el registro sigue funcionando con la extracción local. |
| La extracción tarda o dice "503" | Alta demanda en Google. El sistema reintenta solo y, si no lo logra, usa la extracción local. Completa a mano lo que falte. |
| `npm run test:gemini` falla con HTTP 404 en el modelo | El modelo de `GEMINI_MODEL` no está disponible para tu clave: revisa los nombres vigentes en la [documentación de modelos](https://ai.google.dev/gemini-api/docs/models). Si el modelo no admite `GEMINI_THINKING_LEVEL="minimal"`, el sistema reintenta sin ese parámetro. |

## Sandbox: escenarios de prueba

Todos los datos del sandbox son ficticios.

| Escenario | Contenido | Cómo usarlo |
|---|---|---|
| `ampliado` (por defecto) | 24 casos y 14 colaboradores. Cubre los 5 eventos del catálogo con y sin apremio, 8 casos que **no** deben generar eventos, una licencia médica vigente, una capacitación programada y colaboradores nuevos con poco historial | Selector **Escenario** del encabezado → **Reiniciar sandbox** |
| `base` | Los 6 casos y 8 colaboradores originales de la demo | El mismo selector, `SANDBOX_ESCENARIO=base` en el `.env` o `{"escenario": "base"}` en `POST /api/v1/reiniciar` |

El sandbox se carga **solo cuando no hay datos** (`python_engine/data_store.json` no existe). Si tus datos son de otro escenario que el configurado, por ejemplo porque se crearon antes de que existiera el ampliado, aparece un aviso azul en el encabezado con el botón **Cargar escenario «ampliado»**. No se recargan solos para no borrar lo que hiciste en la demo. Si eliges otro escenario a propósito con el selector, el aviso no aparece.

Para tener una demo aparte sin tocar la principal, define `COBGESTION_DATA_STORE` con la ruta de otro archivo antes de `npm run dev`.

Si el equipo no alcanza a cubrir todas las tareas nuevas, el asignador usa primero los cupos en las tareas críticas y escala a la jefatura las de menor prioridad. El dashboard lo informa en `tareas_sobre_capacidad`.

## Paquete de evidencia

```bash
npm run evidencia
```

Genera `evidencia/<fecha_hora>/` (no se versiona) sobre un repositorio en memoria: no modifica `data_store.json` ni llama a Gemini. Tarda alrededor de un minuto.

> **Qué cifras presentar.** Sirven como resultado las que no dependen del azar: la detección caso por caso, el 100% de tareas con responsable, que nadie con licencia reciba tareas y la alerta inmediata al registrar un comprobante. El **cumplimiento de SLA** y los **tiempos de atención** simulados salen de tiempos de respuesta ficticios: con 10 semillas, los eventos críticos atendidos a tiempo van de ~33% a ~81%. Preséntalos como algo que el sistema *permite medir*, no como un hallazgo sobre Cobgestion. Además, la alerta se mide desde que el comprobante **se registra**: un pantallazo de WhatsApp todavía requiere que alguien lo ingrese.

| Archivo | Contenido |
|---|---|
| `README.md` | Cifras para la presentación y qué no demuestra el paquete |
| `deteccion.md` | Escenario ampliado: eventos esperados frente a detectados, caso por caso, incluidos los controles negativos |
| `recorrido_demo.md` | El caso del auto paso a paso: detección, asignación, cierre coordinado, comprobante nuevo, aviso del CRM, ausencia y vencimiento |
| `simulacion.md` | Una semana simulada con avisos y cambios del CRM a cualquier hora, con sus supuestos y la misma semana repetida con 10 semillas aleatorias |
| `metricas.json`, `pruebas.txt`, `exportaciones/` | Cifras en formato máquina, salida de las pruebas y hojas del repositorio en CSV |
| `checklist_capturas.md` | Capturas de la interfaz que conviene sacar a mano |

## Importación de casos desde el CRM o una planilla

Mientras no exista una integración directa con el CRM, los casos se cargan desde un CSV (Excel → *Guardar como* → CSV).

```bash
npm run importar -- casos.csv --validar                       # revisa sin cambiar nada
npm run importar -- casos.csv                                 # valida y carga
npm run importar -- casos.csv --mapeo docs/mapeo_crm_ejemplo.json   # columnas con otros nombres
```

- Plantilla: [docs/plantilla_carga_casos.csv](docs/plantilla_carga_casos.csv). Mapeo de ejemplo: [docs/mapeo_crm_ejemplo.json](docs/mapeo_crm_ejemplo.json).
- Valida cada fila: campos obligatorios, RUT con dígito verificador, montos, estados del catálogo (sin importar tildes ni mayúsculas), responsables existentes y de su área, fechas y duplicados. El reporte indica el motivo de cada fila rechazada.
- Un caso nuevo se inserta. Uno existente (mismo id o rol de causa) se actualiza solo en los campos editables, y cada diferencia queda en el historial.
- Al terminar se ejecuta el detector: los eventos de los casos cargados quedan creados y asignados.

## Estados de pago

| Estado | Significado | Evento que dispara |
|---|---|---|
| **Informado / por confirmar** | Llegó el aviso o comprobante; falta verificarlo | EC-01: alerta judicial inmediata |
| **Confirmado** | Verificado contra la cartola o la planilla del mandante | EC-03 si la causa sigue activa |
| **Observado / no confirmado** | Diferencias o antecedentes pendientes | EC-02 |

## Licencia

Apache-2.0.
