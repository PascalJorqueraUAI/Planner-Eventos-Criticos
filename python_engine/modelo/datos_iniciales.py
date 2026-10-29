"""
Datos del entorno de pruebas (sandbox).

Simula lo que entregaría la integración con el CRM y las planillas de Cobgestion:
casos, avisos de pago, colaboradores y su historial de tareas atendidas. Las fechas
son relativas al momento de la carga para que la demo siempre esté vigente.

Hay dos escenarios, todos con datos ficticios:
  - "base": 6 casos y 8 colaboradores. Es el escenario mínimo de la demo y el que usan
    las pruebas unitarias originales.
  - "ampliado" (por defecto): los mismos 6 casos y 8 colaboradores más 18 casos y
    6 colaboradores adicionales. Cubre los 5 eventos del catálogo en varias variantes
    (con y sin apremio), casos que NO deben generar eventos, un colaborador con licencia
    médica vigente, otro con una capacitación programada y colaboradores nuevos con poco
    historial. Sirve para probar la robustez del detector y del asignador con más carga.

El escenario se elige con la variable de entorno SANDBOX_ESCENARIO o al reiniciar.
"""

import random
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Dict

from modelo.entidades import AvisoPago, Caso, Colaborador, RegistroDesempeno, a_iso

# (tareas atendidas, tasa de cumplimiento de SLA, horas promedio) por tipo de tarea.
PERFILES = {
    "COL-0001": {  # Camila Valenzuela
        "VERIFICAR_PAGO": (18, 0.94, 5), "ACLARAR_DISCREPANCIA": (9, 0.89, 20),
        "CONTACTAR_DEUDOR": (14, 0.86, 6), "REGISTRAR_PAGO_CRM": (12, 0.92, 8),
        "GESTIONAR_REPACTACION": (7, 0.86, 30),
    },
    "COL-0002": {  # Ignacio Rivas
        "VERIFICAR_PAGO": (11, 0.82, 9), "ACLARAR_DISCREPANCIA": (12, 0.92, 16),
        "CONTACTAR_DEUDOR": (6, 0.67, 10), "REGISTRAR_PAGO_CRM": (9, 0.89, 10),
        "GESTIONAR_REPACTACION": (10, 0.80, 26),
    },
    "COL-0003": {  # Fernanda Soto
        "VERIFICAR_PAGO": (4, 0.75, 7), "CONTACTAR_DEUDOR": (5, 0.80, 5),
        "REGISTRAR_PAGO_CRM": (3, 1.0, 6),
    },
    "COL-0005": {  # Rodrigo Morales
        "EVALUAR_SUSPENSION": (16, 0.88, 3), "FORMALIZAR_SUSPENSION_TERMINO": (10, 0.90, 20),
        "CONFIRMAR_DILIGENCIA": (12, 0.83, 4), "EVALUAR_CURSO_CAUSA": (6, 0.83, 18),
        "REACTIVAR_CAUSA": (5, 0.80, 40),
    },
    "COL-0006": {  # Valentina Tapia
        "EVALUAR_SUSPENSION": (9, 0.78, 5), "FORMALIZAR_SUSPENSION_TERMINO": (13, 0.92, 16),
        "EVALUAR_CURSO_CAUSA": (11, 0.91, 14), "REACTIVAR_CAUSA": (8, 0.88, 36),
        "CONFIRMAR_DILIGENCIA": (5, 0.80, 5),
    },
    "COL-0007": {  # Matías Herrera
        "EVALUAR_SUSPENSION": (5, 0.80, 4), "CONFIRMAR_DILIGENCIA": (7, 0.86, 3),
        "EVALUAR_CURSO_CAUSA": (3, 0.67, 20),
    },
}

TIPOS_COMERCIALES = ["VERIFICAR_PAGO", "ACLARAR_DISCREPANCIA", "REGISTRAR_PAGO_CRM", "CONTACTAR_DEUDOR", "GESTIONAR_REPACTACION"]
TIPOS_JUDICIALES = ["EVALUAR_SUSPENSION", "EVALUAR_CURSO_CAUSA", "FORMALIZAR_SUSPENSION_TERMINO", "CONFIRMAR_DILIGENCIA", "REACTIVAR_CAUSA"]


def _proximo_martes(ahora: datetime) -> datetime:
    dias = (1 - ahora.weekday()) % 7 or 7
    return (ahora + timedelta(days=dias)).replace(hour=9, minute=0, second=0, microsecond=0)


def _colaboradores(ahora: datetime):
    # Las ausencias vienen del calendario: el ciclo del detector aplica la no disponibilidad.
    permiso_camila = {
        "desde": a_iso(ahora - timedelta(hours=20)),
        "hasta": a_iso(_proximo_martes(ahora)),
        "motivo": "Permiso administrativo, regresa el martes",
    }
    vacaciones_rodrigo = {
        "desde": a_iso(ahora + timedelta(hours=30)),
        "hasta": a_iso(ahora + timedelta(days=5, hours=6)),
        "motivo": "Vacaciones (feriado largo)",
    }
    return [
        Colaborador("COL-0001", "Camila Valenzuela", "Comercial", "Ejecutivo Comercial",
                    list(PERFILES["COL-0001"]), capacidad_max=6, tareas_externas=4,
                    ausencias=[permiso_camila]),
        Colaborador("COL-0002", "Ignacio Rivas", "Comercial", "Ejecutivo Comercial",
                    list(PERFILES["COL-0002"]), capacidad_max=5, tareas_externas=2),
        Colaborador("COL-0003", "Fernanda Soto", "Comercial", "Ejecutivo Comercial",
                    list(PERFILES["COL-0003"]), capacidad_max=4, tareas_externas=1),
        Colaborador("COL-0004", "Patricia Lagos", "Comercial", "Jefe Comercial",
                    TIPOS_COMERCIALES, capacidad_max=3),
        Colaborador("COL-0005", "Abg. Rodrigo Morales", "Judicial", "Ejecutivo Judicial",
                    list(PERFILES["COL-0005"]), capacidad_max=6, tareas_externas=4,
                    ausencias=[vacaciones_rodrigo]),
        Colaborador("COL-0006", "Abg. Valentina Tapia", "Judicial", "Ejecutivo Judicial",
                    list(PERFILES["COL-0006"]), capacidad_max=5, tareas_externas=2),
        Colaborador("COL-0007", "Abg. Matías Herrera", "Judicial", "Ejecutivo Judicial",
                    list(PERFILES["COL-0007"]), capacidad_max=4, tareas_externas=1),
        Colaborador("COL-0008", "Abg. Andrés Fuentes", "Judicial", "Jefe Judicial",
                    TIPOS_JUDICIALES, capacidad_max=3),
    ]


def _historial_desempeno(ahora: datetime, perfiles=None, semilla: int = 2026):
    azar = random.Random(semilla)
    registros = []
    for colaborador_id, perfil in (perfiles or PERFILES).items():
        for tipo, (n, tasa, horas) in perfil.items():
            cumplidas = round(n * tasa)
            resultados = [True] * cumplidas + [False] * (n - cumplidas)
            azar.shuffle(resultados)
            for cumplio in resultados:
                registros.append(RegistroDesempeno(
                    colaborador_id=colaborador_id,
                    tipo_tarea=tipo,
                    fecha=a_iso(ahora - timedelta(days=azar.randint(7, 180))),
                    horas_resolucion=round(horas * azar.uniform(0.6, 1.4) * (1 if cumplio else 1.8), 1),
                    cumplio_sla=cumplio,
                ))
    return registros


def _casos(ahora: datetime):
    def hace(**kw):
        return a_iso(ahora - timedelta(**kw))

    def en(**kw):
        return a_iso((ahora + timedelta(**kw)).replace(minute=30, second=0))

    return [
        Caso("CASO-1052", "C-1420-2026", "17° Juzgado Civil de Santiago",
             {"nombre": "Carlos Silva Mendoza", "rut": "16.482.910-K", "email": "carlos.silva@empresa.cl", "telefono": "+56 9 8831 2290"},
             "Forum Servicios Financieros", 4850000,
             {"tipo": "Vehículo", "descripcion": "Automóvil Suzuki Swift 1.2 GLX 2021", "patente": "BB-CL-44"},
             "En negociación", "Orden de incautación vigente", "COL-0001", "COL-0005",
             hace(days=46), hace(hours=3), fecha_diligencia=en(days=1)),
        Caso("CASO-1053", "C-8891-2025", "2° Juzgado de Letras de San Bernardo",
             {"nombre": "María José Contreras Pinto", "rut": "18.291.433-2", "email": "mjcontreras@gmail.com", "telefono": "+56 9 9120 4451"},
             "Banco Santander Chile", 2300000,
             {"tipo": "Bienes muebles", "descripcion": "Mobiliario y artefactos del domicilio"},
             "Acuerdo vigente", "Notificado", "COL-0002", "COL-0006",
             hace(days=72), hace(days=1)),
        Caso("CASO-1054", "C-3042-2026", "7° Juzgado Civil de Santiago",
             {"nombre": "Transportes San Cristóbal SpA", "rut": "77.194.882-5", "email": "contacto@transsancristobal.cl", "telefono": "+56 2 2841 9900"},
             "Scotiabank Chile", 12800000,
             {"tipo": "Vehículo", "descripcion": "Camión tolva Mercedes-Benz Actros", "patente": "KR-WP-19"},
             "En negociación", "Diligencia con receptor programada", "COL-0001", "COL-0005",
             hace(days=117), hace(hours=20), fecha_diligencia=en(days=2)),
        Caso("CASO-1055", "C-1102-2026", "1° Juzgado Civil de Valparaíso",
             {"nombre": "Gonzalo Patricio Alarcón", "rut": "15.772.304-1", "email": "g.alarcon@gmail.com", "telefono": "+56 9 7721 8891"},
             "Banco Falabella", 980000,
             {"tipo": "Sin garantía", "descripcion": "Crédito de consumo sin caución"},
             "Sin contacto", "Notificado", "COL-0002", "COL-0006",
             hace(days=25), hace(days=4)),
        Caso("CASO-1056", "C-5517-2026", "4° Juzgado Civil de Concepción",
             {"nombre": "Comercial Del Pacífico Ltda.", "rut": "76.402.118-3", "email": "finanzas@delpacifico.cl", "telefono": "+56 41 224 9801"},
             "Banco BCI", 6400000,
             {"tipo": "Inmueble", "descripcion": "Bodega comercial, Talcahuano"},
             "Convenio incumplido", "Suspendido preventivo por aviso de pago", "COL-0003", "COL-0007",
             hace(days=95), hace(hours=30)),
        Caso("CASO-1057", "C-2290-2026", "3° Juzgado Civil de Santiago",
             {"nombre": "Rosa Elena Muñoz Castro", "rut": "12.904.556-8", "email": "rosa.munoz@hotmail.com", "telefono": "+56 9 6612 3307"},
             "Banco Itaú", 1750000,
             {"tipo": "Vehículo", "descripcion": "Furgón Peugeot Partner 2019", "patente": "HJ-KT-82"},
             "Acuerdo vigente", "Mandamiento de embargo", "COL-0003", "COL-0006",
             hace(days=60), hace(hours=6)),
    ]


def _avisos(ahora: datetime):
    def hace(**kw):
        return a_iso(ahora - timedelta(**kw))

    return [
        AvisoPago("AVP-0101", "CASO-1052", hace(hours=3), 850000, "Pantallazo cliente (WhatsApp)", "WhatsApp", "informado",
                  {"banco_origen": "Banco de Chile", "numero_operacion": "TRF-8849102", "rut_depositante": "16.482.910-K",
                   "nombre_depositante": "Carlos Silva Mendoza", "comentario": "Cuota convenio auto BB-CL-44", "confianza_ia": 0.98},
                  "Pantallazo recibido por WhatsApp. Pendiente de conciliar contra cartola."),
        AvisoPago("AVP-0102", "CASO-1053", hace(days=1), 400000, "Correo automático banco", "Email", "observado",
                  {"banco_origen": "Banco Santander", "numero_operacion": "SAN-20261023-9941", "rut_depositante": "18.291.433-2",
                   "nombre_depositante": "María José Contreras Pinto", "confianza_ia": 0.95},
                  "La cuota acordada es $450.000; el aviso informa $400.000."),
        AvisoPago("AVP-0103", "CASO-1057", hace(hours=6), 1750000, "Planilla mandante", "Planilla Mandante", "confirmado",
                  {"numero_operacion": "ITAU-LIQ-77120", "rut_depositante": "12.904.556-8"},
                  "Pago total confirmado en la liquidación quincenal de Banco Itaú."),
    ]


# --- Escenario ampliado ------------------------------------------------------------

ESCENARIOS = ("base", "ampliado")
ESCENARIO_POR_DEFECTO = "ampliado"

PERFILES_ADICIONALES = {
    "COL-0009": {  # Diego Castillo: ejecutivo con experiencia
        "VERIFICAR_PAGO": (15, 0.93, 6), "ACLARAR_DISCREPANCIA": (8, 0.88, 18),
        "CONTACTAR_DEUDOR": (12, 0.92, 5), "REGISTRAR_PAGO_CRM": (10, 0.90, 7),
        "GESTIONAR_REPACTACION": (6, 0.83, 28),
    },
    "COL-0010": {  # Constanza Reyes: recién incorporada, poco historial
        "VERIFICAR_PAGO": (3, 1.0, 6), "CONTACTAR_DEUDOR": (2, 1.0, 5), "REGISTRAR_PAGO_CRM": (2, 1.0, 6),
    },
    "COL-0011": {  # Tomás Navarro: capacitación programada
        "VERIFICAR_PAGO": (9, 0.78, 10), "ACLARAR_DISCREPANCIA": (10, 0.90, 15),
        "CONTACTAR_DEUDOR": (7, 0.71, 9), "GESTIONAR_REPACTACION": (9, 0.89, 24),
    },
    "COL-0012": {  # Sofía Paredes: abogada con experiencia
        "EVALUAR_SUSPENSION": (14, 0.93, 3), "FORMALIZAR_SUSPENSION_TERMINO": (11, 0.91, 14),
        "CONFIRMAR_DILIGENCIA": (9, 0.89, 3), "EVALUAR_CURSO_CAUSA": (8, 0.88, 15),
        "REACTIVAR_CAUSA": (4, 0.75, 38),
    },
    "COL-0013": {  # Felipe Ortega: con licencia médica vigente
        "EVALUAR_SUSPENSION": (10, 0.80, 5), "FORMALIZAR_SUSPENSION_TERMINO": (9, 0.89, 18),
        "EVALUAR_CURSO_CAUSA": (6, 0.83, 16), "REACTIVAR_CAUSA": (7, 0.86, 34),
    },
    "COL-0014": {  # Carolina Vidal: abogada junior
        "EVALUAR_SUSPENSION": (2, 1.0, 4), "CONFIRMAR_DILIGENCIA": (3, 0.67, 5),
        "FORMALIZAR_SUSPENSION_TERMINO": (2, 1.0, 12),
    },
}


def _rut(numero: int) -> str:
    """RUT ficticio con dígito verificador válido (módulo 11)."""
    suma, factor = 0, 2
    for digito in reversed(str(numero)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    dv = {11: "0", 10: "K"}.get(resto, str(resto))
    return f"{numero:,}".replace(",", ".") + f"-{dv}"


def _colaboradores_adicionales(ahora: datetime):
    capacitacion_tomas = {
        "desde": a_iso(ahora + timedelta(hours=36)),
        "hasta": a_iso(ahora + timedelta(days=4)),
        "motivo": "Capacitación externa programada",
    }
    licencia_felipe = {
        "desde": a_iso(ahora - timedelta(days=2)),
        "hasta": a_iso(ahora + timedelta(days=3)),
        "motivo": "Licencia médica",
    }
    p = PERFILES_ADICIONALES
    return [
        Colaborador("COL-0009", "Diego Castillo", "Comercial", "Ejecutivo Comercial",
                    list(p["COL-0009"]), capacidad_max=7, tareas_externas=2),
        Colaborador("COL-0010", "Constanza Reyes", "Comercial", "Ejecutivo Comercial",
                    list(p["COL-0010"]), capacidad_max=5, tareas_externas=0),
        Colaborador("COL-0011", "Tomás Navarro", "Comercial", "Ejecutivo Comercial",
                    list(p["COL-0011"]), capacidad_max=4, tareas_externas=1,
                    ausencias=[capacitacion_tomas]),
        Colaborador("COL-0012", "Abg. Sofía Paredes", "Judicial", "Ejecutivo Judicial",
                    list(p["COL-0012"]), capacidad_max=7, tareas_externas=2),
        Colaborador("COL-0013", "Abg. Felipe Ortega", "Judicial", "Ejecutivo Judicial",
                    list(p["COL-0013"]), capacidad_max=5, tareas_externas=3,
                    ausencias=[licencia_felipe]),
        Colaborador("COL-0014", "Abg. Carolina Vidal", "Judicial", "Ejecutivo Judicial",
                    list(p["COL-0014"]), capacidad_max=5, tareas_externas=0),
    ]


# Evento(s) que el detector debe crear al cargar cada caso del escenario ampliado.
# Se usa en las pruebas y en el reporte de evidencia para comparar lo esperado con lo detectado.
EVENTOS_ESPERADOS_AMPLIADO = {
    "CASO-1052": ["EC-01"], "CASO-1053": ["EC-02"], "CASO-1054": ["EC-04"],
    "CASO-1055": [], "CASO-1056": ["EC-05"], "CASO-1057": ["EC-03"],
    "CASO-1058": ["EC-01"], "CASO-1059": ["EC-01"], "CASO-1060": ["EC-01"],
    "CASO-1061": ["EC-02"], "CASO-1062": ["EC-02"], "CASO-1063": ["EC-03"],
    "CASO-1064": ["EC-03"], "CASO-1065": ["EC-04"], "CASO-1066": ["EC-04"],
    "CASO-1067": ["EC-05"], "CASO-1068": ["EC-05"],
    # Casos que NO deben generar eventos (controles negativos).
    "CASO-1069": [], "CASO-1070": [], "CASO-1071": [], "CASO-1072": [],
    "CASO-1073": [], "CASO-1074": [], "CASO-1075": [],
}


def _casos_adicionales(ahora: datetime):
    def hace(**kw):
        return a_iso(ahora - timedelta(**kw))

    def en(**kw):
        return a_iso((ahora + timedelta(**kw)).replace(minute=30, second=0))

    def caso(num, rol, tribunal, deudor, rut, email, mandante, monto, bien, comercial, judicial,
             resp_com, resp_jud, dias, actualizado, diligencia=None):
        return Caso(f"CASO-{num}", rol, tribunal,
                    {"nombre": deudor, "rut": _rut(rut), "email": email, "telefono": f"+56 9 {7000 + num % 1000:04d} {num * 37 % 10000:04d}"},
                    mandante, monto, bien, comercial, judicial, resp_com, resp_jud,
                    hace(days=dias), actualizado, fecha_diligencia=diligencia)

    auto = lambda d, p: {"tipo": "Vehículo", "descripcion": d, "patente": p}
    return [
        # EC-01 con apremio (crítico)
        caso(1058, "C-4410-2026", "12° Juzgado Civil de Santiago", "Héctor Ramírez Loyola", 14552318,
             "h.ramirez@correo.cl", "Forum Servicios Financieros", 5900000, auto("Camioneta Toyota Hilux 2020", "LP-RT-31"),
             "En negociación", "Mandamiento de embargo", "COL-0009", "COL-0012", 80, hace(hours=2)),
        # EC-01 sin apremio
        caso(1059, "C-0912-2026", "5° Juzgado Civil de Santiago", "Paula Andrea Fuentes Rojas", 17834552,
             "paula.fuentes@correo.cl", "Banco Santander Chile", 1200000, {"tipo": "Sin garantía", "descripcion": "Crédito de consumo"},
             "Acuerdo vigente", "En tramitación", "COL-0010", "COL-0014", 40, hace(hours=5)),
        # EC-01 con receptor programado: el aviso pendiente prevalece sobre EC-04
        caso(1060, "C-3377-2026", "2° Juzgado Civil de Rancagua", "Luis Alberto Soto Vera", 13209877,
             "lsoto@correo.cl", "Banco BCI", 7300000, auto("Automóvil Hyundai Tucson 2022", "RZ-KP-60"),
             "En negociación", "Diligencia con receptor programada", "COL-0002", "COL-0006", 55, hace(hours=1),
             diligencia=en(hours=30)),
        # EC-02 sin apremio
        caso(1061, "C-7781-2025", "3° Juzgado de Letras de Puente Alto", "Andrea Molina Pérez", 16020114,
             "amolina@correo.cl", "Banco Falabella", 860000, {"tipo": "Sin garantía", "descripcion": "Tarjeta de crédito"},
             "Acuerdo vigente", "Notificado", "COL-0011", "COL-0007", 120, hace(days=1)),
        # EC-02 con apremio (crítico)
        caso(1062, "C-5120-2026", "9° Juzgado Civil de Santiago", "Servicios Logísticos Andes SpA", 76881204,
             "pagos@logisticaandes.cl", "Scotiabank Chile", 15400000, auto("Furgón Hyundai H-1 2021", "PX-LW-55"),
             "En negociación", "Orden de incautación vigente", "COL-0009", "COL-0012", 70, hace(hours=4)),
        # EC-03 sin apremio
        caso(1063, "C-2041-2026", "1° Juzgado Civil de Temuco", "Ricardo Esteban Lagos", 11908276,
             "rlagos@correo.cl", "Banco de Chile", 2100000, auto("Motocicleta Honda CB500 2022", "KTZ-41"),
             "Acuerdo vigente", "En tramitación", "COL-0010", "COL-0014", 90, hace(hours=8)),
        # EC-03 con apremio (crítico)
        caso(1064, "C-6690-2026", "2° Juzgado Civil de Antofagasta", "Minera Los Cóndores Ltda.", 77402965,
             "finanzas@loscondores.cl", "Banco Itaú", 22800000, {"tipo": "Maquinaria", "descripcion": "Retroexcavadora CAT 420"},
             "Acuerdo vigente", "Mandamiento de embargo", "COL-0002", "COL-0013", 150, hace(hours=10)),
        # EC-04: incautación con diligencia en 20 h (crítico)
        caso(1065, "C-1188-2026", "18° Juzgado Civil de Santiago", "Javier Ignacio Pino", 15334708,
             "jpino@correo.cl", "Forum Servicios Financieros", 6100000, auto("Automóvil Kia Rio 2020", "JH-TS-18"),
             "En negociación", "Orden de incautación vigente", "COL-0003", "COL-0005", 64, hace(hours=12),
             diligencia=en(hours=20)),
        # EC-04: receptor con diligencia en 60 h y acuerdo vigente
        caso(1066, "C-4021-2026", "1° Juzgado Civil de La Serena", "Claudia Henríquez Díaz", 12773490,
             "chenriquez@correo.cl", "Banco BCI", 3900000, auto("Automóvil Chevrolet Sail 2019", "HY-ZD-72"),
             "Acuerdo vigente", "Diligencia con receptor programada", "COL-0009", "COL-0012", 101, hace(days=2),
             diligencia=en(hours=60)),
        # EC-05: convenio incumplido con suspensión formal
        caso(1067, "C-8834-2025", "3° Juzgado Civil de Viña del Mar", "Ferretería El Roble Ltda.", 76119042,
             "contacto@elroble.cl", "Banco Santander Chile", 4700000, {"tipo": "Inmueble", "descripcion": "Local comercial, Quilpué"},
             "Convenio incumplido", "Suspendido formalmente en tribunal", "COL-0011", "COL-0013", 210, hace(days=1)),
        # EC-05: convenio incumplido con suspensión preventiva
        caso(1068, "C-0573-2026", "4° Juzgado Civil de Santiago", "Marcela Jiménez Toro", 18447201,
             "mjimenez@correo.cl", "Banco Falabella", 1350000, auto("Automóvil Nissan Versa 2018", "GT-PL-09"),
             "Convenio incumplido", "Suspendido preventivo por aviso de pago", "COL-0003", "COL-0006", 88, hace(hours=20)),
        # --- Controles negativos: no deben generar eventos ---
        # Diligencia en 5 días: fuera de la ventana de 72 h (entra en la ventana al avanzar el reloj).
        caso(1069, "C-3915-2026", "10° Juzgado Civil de Santiago", "Roberto Cárdenas Fuentes", 14098325,
             "rcardenas@correo.cl", "Scotiabank Chile", 8200000, auto("Camioneta Ford Ranger 2021", "PR-GH-23"),
             "En negociación", "Orden de incautación vigente", "COL-0009", "COL-0012", 75, hace(days=1),
             diligencia=en(days=5)),
        # Causa terminada por pago con aviso confirmado.
        caso(1070, "C-1503-2025", "6° Juzgado Civil de Santiago", "Elena Vargas Muñoz", 10882645,
             "evargas@correo.cl", "Banco de Chile", 950000, {"tipo": "Sin garantía", "descripcion": "Crédito de consumo"},
             "Pagado", "Terminado por pago", "COL-0010", "COL-0014", 300, hace(days=10)),
        # Pago confirmado con la causa ya suspendida formalmente.
        caso(1071, "C-2266-2026", "2° Juzgado Civil de Concepción", "Agrícola Santa Rita SpA", 76550318,
             "admin@santarita.cl", "Banco Itaú", 9800000, {"tipo": "Maquinaria", "descripcion": "Tractor John Deere 5075E"},
             "Acuerdo vigente", "Suspendido formalmente en tribunal", "COL-0002", "COL-0007", 140, hace(days=3)),
        # Sin avisos ni apremio.
        caso(1072, "C-7720-2026", "1° Juzgado Civil de Talca", "Sergio Muñoz Bravo", 13661054,
             "smunoz@correo.cl", "Banco Falabella", 640000, {"tipo": "Sin garantía", "descripcion": "Tarjeta de crédito"},
             "Sin contacto", "Demanda presentada", "COL-0011", "COL-0006", 12, hace(days=6)),
        caso(1073, "C-6158-2026", "8° Juzgado Civil de Santiago", "Daniela Correa Silva", 19203887,
             "dcorrea@correo.cl", "Banco Santander Chile", 1100000, auto("Automóvil Suzuki Baleno 2019", "FK-RW-37"),
             "En negociación", "Notificado", "COL-0003", "COL-0014", 33, hace(days=2)),
        # Aviso informado, pero la causa ya terminó por pago.
        caso(1074, "C-0844-2025", "11° Juzgado Civil de Santiago", "Patricio Herrera Lillo", 12035761,
             "pherrera@correo.cl", "Banco BCI", 2400000, {"tipo": "Sin garantía", "descripcion": "Crédito de consumo"},
             "Pagado", "Terminado por pago", "COL-0010", "COL-0012", 260, hace(days=1)),
        # Fecha de diligencia registrada, pero la causa no tiene apremio en curso.
        caso(1075, "C-5530-2026", "3° Juzgado Civil de Santiago", "Inversiones Altamira Ltda.", 76990127,
             "contacto@altamira.cl", "Scotiabank Chile", 5200000, {"tipo": "Inmueble", "descripcion": "Oficina, Providencia"},
             "Acuerdo vigente", "En tramitación", "COL-0009", "COL-0007", 180, hace(days=4),
             diligencia=en(hours=40)),
    ]


def _avisos_adicionales(ahora: datetime, casos):
    def hace(**kw):
        return a_iso(ahora - timedelta(**kw))

    rut = {c.id: c.deudor["rut"] for c in casos}
    nombre = {c.id: c.deudor["nombre"] for c in casos}

    def aviso(num, caso_id, horas, monto, origen, canal, estado, operacion, banco, obs, confianza=None):
        datos = {"banco_origen": banco, "numero_operacion": operacion, "rut_depositante": rut[caso_id],
                 "nombre_depositante": nombre[caso_id]}
        if confianza is not None:
            datos["confianza_ia"] = confianza
        # Mismo formato que los ids que asigna el repositorio (AVP-0104), para que no convivan dos estilos.
        return AvisoPago(f"AVP-{num:04d}", caso_id, hace(hours=horas), monto, origen, canal, estado, datos, obs)

    return [
        aviso(104, "CASO-1058", 2, 600000, "Pantallazo cliente (WhatsApp)", "WhatsApp", "informado",
              "TRF-5530218", "BancoEstado", "Cuota de convenio enviada por WhatsApp.", 0.93),
        aviso(105, "CASO-1059", 5, 150000, "Correo automático banco", "Email", "informado",
              "SAN-20261027-4410", "Banco Santander", "Aviso automático de transferencia recibida.", 0.97),
        aviso(106, "CASO-1060", 1, 1300000, "Correo cliente", "Email", "informado",
              "BCI-88120934", "Banco BCI", "El deudor adjunta comprobante y pide suspender la diligencia."),
        aviso(107, "CASO-1061", 30, 90000, "Portal deudor", "Portal Deudor", "observado",
              "FAL-3349102", "Banco Falabella", "La cuota pactada es $120.000; se informó $90.000."),
        aviso(108, "CASO-1062", 4, 2500000, "Pantallazo cliente (correo)", "Email", "observado",
              "", "Scotiabank", "Comprobante ilegible: no se distingue el N° de operación.", 0.61),
        aviso(109, "CASO-1063", 8, 2100000, "Planilla mandante", "Planilla Mandante", "confirmado",
              "BCH-LIQ-20931", "Banco de Chile", "Pago total confirmado en la planilla de Banco de Chile."),
        aviso(110, "CASO-1064", 10, 22800000, "Planilla mandante", "Planilla Mandante", "confirmado",
              "ITAU-LIQ-77344", "Banco Itaú", "Pago total confirmado en la liquidación quincenal."),
        aviso(111, "CASO-1070", 240, 950000, "Planilla mandante", "Planilla Mandante", "confirmado",
              "BCH-LIQ-19022", "Banco de Chile", "Pago total; causa ya terminada."),
        aviso(112, "CASO-1071", 72, 9800000, "Planilla mandante", "Planilla Mandante", "confirmado",
              "ITAU-LIQ-77002", "Banco Itaú", "Pago confirmado; suspensión formal ya presentada."),
        aviso(113, "CASO-1074", 6, 100000, "Correo cliente", "Email", "informado",
              "BCI-77001234", "Banco BCI", "Abono informado sobre una causa ya terminada."),
    ]


def crear_datos_iniciales(ahora: datetime, escenario: str = ESCENARIO_POR_DEFECTO) -> Dict[str, Any]:
    if escenario not in ESCENARIOS:
        raise ValueError(f"Escenario desconocido: {escenario}. Opciones: {', '.join(ESCENARIOS)}")
    casos = _casos(ahora)
    avisos = _avisos(ahora)
    colaboradores = _colaboradores(ahora)
    desempeno = _historial_desempeno(ahora)
    if escenario == "ampliado":
        adicionales = _casos_adicionales(ahora)
        casos += adicionales
        avisos += _avisos_adicionales(ahora, adicionales)
        colaboradores += _colaboradores_adicionales(ahora)
        desempeno += _historial_desempeno(ahora, PERFILES_ADICIONALES, semilla=2027)
    ultimo = lambda ids: max(int(i.split("-")[1]) for i in ids)
    return {
        "casos": [asdict(c) for c in casos],
        "avisos": [asdict(a) for a in avisos],
        "eventos": [],
        "tareas": [],
        "colaboradores": [asdict(c) for c in colaboradores],
        "historial_desempeno": [asdict(r) for r in desempeno],
        "historial": [],
        "tratamientos": [],
        "meta": {
            "contadores": {
                "casos": ultimo(c.id for c in casos),
                "avisos": ultimo(a.id for a in avisos),
                "colaboradores": len(colaboradores),
            },
            "cargado_en": a_iso(ahora),
            "ultimo_escaneo": None,
            "escenario": escenario,
        },
    }
