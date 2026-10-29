# Puesta en marcha en Cobgestion

Guía para llevar el prototipo del Sistema Integrado de Eventos Críticos desde el sandbox a un piloto con datos reales.

## 1. Estado actual

| Componente | Estado | Evidencia |
|---|---|---|
| Repositorio centralizado (historial de cambios, exportación a Excel) | Desarrollado y probado en sandbox | `npm test`, `npm run evidencia` |
| Detector de eventos críticos (catálogo EC-01 a EC-05, prioridad por apremio) | Desarrollado y probado en sandbox | `evidencia/<fecha>/deteccion.md` |
| Asignación y seguimiento (RACI, método húngaro, ausencias, escalamiento, cierre coordinado) | Desarrollado y probado en sandbox | `evidencia/<fecha>/recorrido_demo.md` |
| Dashboard de trazabilidad | Desarrollado | Interfaz web, `checklist_capturas.md` |
| API REST para el CRM, comprobantes y planillas de mandantes | Desarrollada | `server.ts`, rutas `/api/v1/*` |
| Importador de casos desde CSV del CRM o de una planilla | Desarrollado y probado | `python_engine/importar_casos.py`, plantilla en `docs/` |
| Extracción de comprobantes con IA y protección de datos | Desarrollada; Gemini apagado por defecto | README, sección de protección de datos |
| Validación con Cobgestion del catálogo, la matriz RACI y los SLA | **Pendiente** | — |
| Conexión con el CRM real y datos reales | **Pendiente** (requiere acceso de Cobgestion) | — |

## 2. Qué necesitamos de Cobgestion

- [ ] Una sesión para validar el **catálogo de eventos críticos** (EC-01 a EC-05), sus condiciones y las tareas de cada área.
- [ ] Validar la **matriz RACI** y los **SLA** por tipo de tarea (hoy: 4 h para Judicial cuando hay apremio).
- [ ] La lista de colaboradores que participarán: nombre, área, cargo, tipos de tarea que atienden y capacidad aproximada.
- [ ] Una **exportación del CRM** con los casos compartidos entre Comercial y Judicial (idealmente anonimizada para el piloto) y el nombre de sus columnas, para preparar el mapeo.
- [ ] Un responsable interno del proceso (dueño del piloto) y un contacto de TI.
- [ ] Un equipo o servidor en la red interna donde instalar el sistema.
- [ ] Decisión sobre la extracción con Gemini: solo se activa con facturación en Google Cloud, el DPA de Google aceptado y validación legal (Ley 19.628 y Ley 21.719). Sin esto, el sistema funciona con extracción local y registro manual.

## 3. Requisitos técnicos

| Elemento | Requisito |
|---|---|
| Sistema operativo | Windows 10/11 o Linux |
| Node.js | 20.19 o superior |
| Python | 3.10 o superior, solo biblioteca estándar |
| Red | Acceso desde los equipos de Comercial y Judicial al puerto configurado (3000 por defecto) |
| Respaldo | Copia diaria de `python_engine/data_store.json` y de las exportaciones CSV |

## 4. Instalación

```bash
git clone <URL_DEL_REPOSITORIO>
cd Planner-Eventos-Criticos
npm install
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
npm test                    # todas las pruebas deben pasar
npm run build
npm start                   # http://<servidor>:3000
```

## 5. Carga inicial de casos

1. Exportar los casos desde el CRM a CSV (o guardar la planilla de Excel como CSV).
2. Si los nombres de columna no coinciden con `docs/plantilla_carga_casos.csv`, copiar `docs/mapeo_crm_ejemplo.json` y escribir a la derecha el nombre de cada columna del CRM.
3. Validar sin cargar nada:
   ```bash
   py -3 python_engine/importar_casos.py casos.csv --mapeo mapeo.json --validar
   ```
   El reporte indica filas válidas, filas rechazadas con su motivo (RUT, estados, responsables, fechas) y columnas ignoradas.
4. Corregir el archivo y cargar:
   ```bash
   py -3 python_engine/importar_casos.py casos.csv --mapeo mapeo.json
   ```
   Al terminar se ejecuta el detector: los eventos críticos de los casos cargados quedan creados y asignados.

La misma carga está disponible en la API: `POST /api/v1/importar-casos` con `{ "csv": "...", "mapeo": {...}, "solo_validar": true }`.

## 6. Operación diaria durante el piloto

| Entrada | Cómo llega al sistema |
|---|---|
| Cambios de casos en el CRM | Exportación diaria con el importador; o, si TI lo habilita, el CRM llama a `PATCH /api/v1/casos/:id` |
| Comprobantes de pago (WhatsApp, correo, pantallazos) | Formulario *Registrar comprobante* de la interfaz, o `POST /api/v1/avisos` |
| Planillas de mandantes | `POST /api/v1/planillas-mandante` |
| Ausencias del personal | Interfaz o `POST /api/v1/colaboradores/:id/ausencias` |

Lo único manual para los equipos es **marcar cada tarea como atendida** con su resultado.

## 7. Plan de piloto (4 semanas)

| Semana | Actividades | Entregable | Condición para avanzar |
|---|---|---|---|
| 1 | Demo con el sponsor y las áreas; validación del catálogo, la RACI y los SLA; instalación; carga inicial | Catálogo y RACI validados; casos cargados | Sponsor aprueba reglas y entrega accesos |
| 2 | Operación en paralelo con 1 ejecutivo comercial y 1 judicial: el sistema alerta y el proceso actual sigue igual | Registro de alertas frente a lo que se coordinó por WhatsApp | Sin falsas alertas relevantes |
| 3 | Operación asistida: las tareas se atienden en el sistema | Tareas atendidas con resultado y SLA | Uso diario por ambos ejecutivos |
| 4 | Medición de indicadores frente a la línea base y decisión de continuidad | Informe de resultados | Metas alcanzadas o plan de ajuste |

## 8. Indicadores a medir

| Indicador | Línea base (diagnóstico) | Meta |
|---|---|---|
| Diferencias en la fecha de última gestión | 51 | Menos de 16 (−70%) |
| Cambios críticos comunicados al responsable | Por medir en la semana 1 | Más de 90% |
| Casos compartidos centralizados | Por medir | Al menos 95% |
| Coordinación por canal manual | Por medir | Menos de 10% |
| Cambios con responsable asignado | Por medir | Más de 90% |
| Tiempo de detección de conflictos | Mediana 12,4 h (10% más lento: más de 65 h) | Meta a acordar con el sponsor |

## 9. Pendientes técnicos antes de producción

No se implementaron en el prototipo y deben resolverse antes de un uso con más usuarios:

- Autenticación de usuarios y permisos por rol (hoy el usuario se informa en cada solicitud).
- Base de datos multiusuario (por ejemplo PostgreSQL o SQLite) en lugar del archivo JSON.
- Notificaciones por correo o mensajería además de la interfaz.
- HTTPS y despliegue en un servidor administrado por TI.
- Lectura automática de correos con comprobantes (segunda versión).

## 10. Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| Acceso tardío a los datos del CRM | Usar el importador con exportaciones CSV; no depende de una integración directa |
| Reglas del catálogo que no reflejan la operación real | Validarlas en la semana 1 y operar en paralelo en la semana 2 antes de depender del sistema |
| Resistencia al cambio de los equipos | Piloto acotado a dos ejecutivos; lo único nuevo para ellos es marcar las tareas atendidas |
| Exceso de alertas | Revisar en la semana 2 las alertas que no generaron acción y ajustar condiciones |
| Datos personales | Gemini apagado por defecto; seudonimización y registro de tratamientos si se activa |
| Pérdida de datos por el archivo JSON | Respaldo diario; migrar a base de datos antes de producción |
