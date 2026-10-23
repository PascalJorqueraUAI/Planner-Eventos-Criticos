# Cobgestion LegalTech - Sistema Integrado de Detección de Eventos Críticos

Plataforma integral LegalTech desarrollada para **Cobgestion**, especializada en la cobranza judicial y extrajudicial. El sistema resuelve el cuello de botella de coordinación entre el **Área Comercial** y el **Área Judicial**, procesando tanto datos no estructurados (pantallazos de WhatsApp, transferencias bancarias por correo) como planillas estructuradas de mandantes (bancos y financieras), implementando un motor de reglas en **Python 3.10** y una interfaz interactiva de gestión en tiempo real.

---

## 📌 Contexto y Problema de Negocio

En la cobranza judicial, un desfasaje de información entre Comercial y Judicial puede ocasionar graves pérdidas económicas y daños reputacionales:

> **Caso Real de Referencia:**
> Un día viernes se recibió un comprobante de pago por transferencia. Debido a un fin de semana largo, la ejecutiva comercial lo revisó el martes y tardó en procesarlo. Como el área Judicial no tenía conocimiento de este antecedente, el caso judicial continuó sin suspensión y **se incautó indebidamente el vehículo del deudor**. Cobgestion tuvo que asumir los costos de grúa, receptor, custodia y costas judiciales (~**$600.000 CLP**) para restituir el automóvil.

### Solución Implementada:
1. **Definición de Evento Crítico:** Cualquier antecedente relevante (como un aviso de pago aún sin conciliar) que requiere que otra área tome una decisión en un plazo definido.
2. **Detección Inmediata:** Todo comprobante en estado `Informado / por confirmar` dispara **inmediatamente** una alerta judicial preventiva (SLA 4 horas en casos vehiculares), sin esperar a la conciliación definitiva de Comercial.
3. **Gestión Paralela:** Se crean dos tareas simultáneas e independientes (una para Comercial y otra para Judicial).
4. **Regla de Cierre Coordinado:** El evento crítico **no se cierra** si Comercial confirma el pago pero Judicial aún no suspende la causa en tribunales.

---

## 🚀 Requisitos Previos

- **Node.js** >= 18.x (incluye `npm` y `npx`)
- **Python** >= 3.10 (con módulos de biblioteca estándar: `unittest`, `json`, `csv`, `dataclasses`)
- *(Opcional)* **Clave de API Gemini (`GEMINI_API_KEY`)**: Para la extracción asistida por visión/OCR multimodal con el modelo `gemini-3.8-flash`. Si no se configura una clave, el sistema utiliza un extractor heurístico inteligente de respaldo.

---

## 🛠️ Instalación y Puesta en Marcha

### 1. Clonar el Repositorio
```bash
git clone <URL_DE_TU_REPOSITORIO_GITHUB>
cd cobgestion-legaltech
```

### 2. Configurar Variables de Entorno
Crea tu archivo `.env` a partir del ejemplo:
```bash
cp .env.example .env
```

Contenido del archivo `.env`:
```env
# Clave para OCR y extracción estructurada con IA (opcional, cuenta con fallback automático)
GEMINI_API_KEY="TU_API_KEY_DE_GEMINI"

# Puerto y URL de la aplicación
PORT=3000
APP_URL="http://localhost:3000"
```

### 3. Instalar Dependencias del Proyecto
```bash
npm install
```

### 4. Ejecutar el Servidor Full-Stack (Desarrollo)
El servidor Express monta la API, ejecuta el motor de Python como subproceso e inicia la interfaz Vite en el puerto 3000:
```bash
npm run dev
```

Abre tu navegador en:
```
http://localhost:3000
```

---

## 🐍 Ejecución Directa del Motor Python (CLI & Scripts)

El núcleo de reglas de negocio está implementado en Python y puede ser ejecutado directamente desde la terminal o integrado en pipelines automatizados:

### Consultar el Estado del Repositorio y Ahorros
```bash
python3 python_engine/cli.py status
```
*Salida en JSON con total de casos, eventos activos, alertas judiciales pendientes y CLP ahorrado en costas prevenidas.*

### Ejecutar la Suite de Pruebas Unitarias de Python
```bash
python3 python_engine/test_cobgestion.py
# O mediante npm:
npm run test:py
```
*Ejecuta 5 pruebas formales con `unittest` que validan la detección inmediata, la regla de bloqueo de cierre prematuro, el riesgo de 600.000 CLP y la conciliación batch.*

### Exportar las 6 Hojas del Repositorio a Excel / CSV
```bash
python3 python_engine/cli.py export-excel
```
*Genera los archivos compatibles con Excel en `./exports/`: `Cobgestion_Casos.csv`, `Cobgestion_Avisos_Pago.csv`, `Cobgestion_Eventos_Criticos.csv`, `Cobgestion_Tareas.csv`, `Cobgestion_Pagos_Conciliados.csv` e `Cobgestion_Historial.csv`.*

### Restablecer Caso Demostrativo
```bash
python3 python_engine/cli.py reset-data
```

---

## 🧪 Pruebas Unitarias Automatizadas

El proyecto cuenta con suites de pruebas unitarias tanto en Python como en TypeScript:

```bash
# Correr tests unitarios de Python
npm run test:py

# Correr tests unitarios de TypeScript (Node.js test runner nativo)
npm test

# Validación estática de tipos (TypeScript)
npm run lint
```

---

## 🏛️ Arquitectura y Detalle de Módulos

```
cobgestion-legaltech/
├── python_engine/                     # Motor Central en Python 3.10
│   ├── models.py                      # Dataclasses de las 6 entidades del repositorio
│   ├── detector_eventos.py            # Reglas de negocio, SLA y validación de cierre
│   ├── conciliador_mandantes.py       # Algoritmo de conciliación de planillas estructuradas
│   ├── repositorio_cobgestion.py      # Persistencia, auditoría y exportación a Excel
│   ├── cli.py                         # Interfaz CLI invocada por Express y scripts
│   ├── test_cobgestion.py             # Suite formal de pruebas con unittest
│   └── data_store.json                # Base de datos centralizada
├── src/                               # Frontend React + Tailwind CSS
│   ├── components/
│   │   ├── Header.tsx                 # Banner de alerta crítica y contadores en vivo
│   │   ├── CriticalEventsView.tsx     # Gestión paralela dual (Comercial vs Judicial)
│   │   ├── JudicialModule.tsx         # Radar de causas y generador de escritos OJV
│   │   ├── CommercialModule.tsx       # Bandeja de verificación de comprobantes
│   │   ├── UnstructuredIngestionModal.tsx # OCR asistido por IA (Gemini 3.8 Flash)
│   │   ├── MandanteReconcileView.tsx  # Cruce batch de planillas de mandantes
│   │   ├── PythonEngineConsole.tsx    # Terminal interactiva y visor de código Python
│   │   ├── TraceabilityDashboard.tsx  # Métricas de impacto y registro de auditoría
│   │   └── CaseDetailsModal.tsx       # Ficha del expediente judicial
│   ├── domain/                        # Tipos e interfaces TypeScript del dominio
│   ├── App.tsx                        # Integración reactiva full-stack
│   └── main.tsx                       # Punto de entrada de la UI
├── server.ts                          # Servidor Express, puente Python y Gemini API
├── package.json                       # Scripts y dependencias
└── vite.config.ts                     # Configuración de compilación Vite
```

### 1. 🚨 Centro de Eventos Críticos (`CriticalEventsView`)
- Visualización en **tarjetas paralelas divididas**:
  - **Columna Izquierda (Área Comercial):** Verificación del comprobante contra cartola bancaria. Permite marcar como `Confirmado` u `Observado / no confirmado`.
  - **Columna Derecha (Área Judicial):** Alerta prioritaria con SLA de 4 horas para frenar diligencias de incautación de vehículos o embargos.
- **Salvaguarda Cobgestion:** Si Comercial marca el pago como confirmado, el evento **permanece abierto** con advertencia visual hasta que Judicial registra la suspensión formal en tribunales.

### 2. ⚖️ Módulo Judicial (`JudicialModule`)
- Radar de causas judiciales clasificadas por riesgo procesal:
  - *Orden de incautación vigente* (Vehículos con alto riesgo de pérdida de $600.000 CLP).
  - *Diligencia con receptor programada*.
  - *Mandamiento de embargo*.
  - *Suspendidos preventivos* (Casos salvados oportunamente).
- **Generador de Escrito OJV en 1 Clic:** Redacta automáticamente el escrito legal chileno (*"SE TENGA PRESENTE COMPROBANTE DE PAGO Y SE SUSPENDA DILIGENCIA DE INCAUTACIÓN / EMBARGO"*) con los datos de la causa, tribunal, receptor, deudor y patente del vehículo, listo para copiar y presentar en la Oficina Judicial Virtual.

### 3. 💼 Módulo Comercial (`CommercialModule`)
- Bandeja de entrada de comprobantes recibidos (`Avisos_Pago`).
- Filtros por estado: `Por Confirmar`, `Confirmados` y `Observados`.
- Inspección de datos extraídos (Banco emisor, N° transacción, titular, monto CLP y porcentaje de confianza IA).

### 4. 🔍 Ingesta de Datos No Estructurados con IA (`UnstructuredIngestionModal`)
- Resuelve la recepción caótica de antecedentes (pantallazos de WhatsApp, transferencias móviles, fotos de depósitos en caja vecina o correos de bancos).
- Utiliza **Gemini 3.8 Flash** vía `/api/gemini/extract-receipt` para transformar texto o imágenes no estructuradas en datos limpios:
  - Monto exacto (CLP)
  - Banco de origen y destino
  - Número de operación / comprobante
  - RUT y nombre del depositante
- Cuenta con **4 casos chilenos reales precargados** para pruebas inmediatas con un solo clic (incluyendo el caso del automóvil Suzuki Swift patente BB-CL-44).

### 5. 📊 Planillas de Mandantes (`MandanteReconcileView`)
- Gestión de liquidaciones estructuradas enviadas periódicamente por bancos y financieras (Santander, Forum, Scotiabank, CMR).
- **Conciliación masiva:** Cruza automáticamente los códigos de operación y RUT contra los avisos informados, detectando discrepancias de monto al instante.

### 6. 🐍 Motor Python & Terminal (`PythonEngineConsole`)
- Consola web interactiva con acceso a la CLI de Python.
- Permite ejecutar `python3 python_engine/test_cobgestion.py` desde el navegador y ver la salida estándar en vivo.
- Visor de código fuente de los módulos Python desarrollados para Cobgestion.
- Botón de exportación a las 6 hojas de cálculo en formato CSV compatible con Microsoft Excel.

### 7. 📈 Dashboard de Trazabilidad (`TraceabilityDashboard`)
- Métricas del proyecto Capstone:
  - **Pérdidas Prevenidas:** Contador en tiempo real del dinero ahorrado en costas indebidas ($600.000 CLP por cada incautación suspendida a tiempo).
  - **Tasa de Cumplimiento de SLA Judicial:** Medición del tiempo de reacción de los abogados frente a comprobantes recibidos.
  - **Historial Inmutable:** Auditoría con fecha, hora, usuario, área, acción ejecutada y detalle de cada decisión tomada en el sistema.

---

## 📋 Estados de Pago Definidos

| Estado | Significado | ¿Genera Alerta Judicial? |
| :--- | :--- | :--- |
| **Informado / por confirmar** | Se recibió el comprobante o aviso, pendiente de verificar contra la cartola. | **Sí, de forma inmediata**, para que Judicial revise el caso y suspenda apremios si corresponde. |
| **Confirmado** | El pago fue verificado y conciliado contra la fuente o liquidación del mandante. | **Sí**, para actualizar las tareas y registrar el avance hacia el cierre coordinado. |
| **Observado / no confirmado** | Existen diferencias en el monto, comprobante ilegible o antecedentes pendientes. | **Sí**, para requerir revisión a Comercial y evaluar el curso de la causa en Judicial. |

---

## 📄 Licencia

Desarrollado bajo licencia Apache-2.0 para **Cobgestion LegalTech SpA**.
