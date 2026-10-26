"""
Datos del entorno de pruebas (sandbox).

Simula lo que entregaría la integración con el CRM y las planillas de Cobgestion:
casos, avisos de pago, colaboradores y su historial de tareas atendidas. Las fechas
son relativas al momento de la carga para que la demo siempre esté vigente.
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


def _historial_desempeno(ahora: datetime):
    azar = random.Random(2026)
    registros = []
    for colaborador_id, perfil in PERFILES.items():
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


def crear_datos_iniciales(ahora: datetime) -> Dict[str, Any]:
    return {
        "casos": [asdict(c) for c in _casos(ahora)],
        "avisos": [asdict(a) for a in _avisos(ahora)],
        "eventos": [],
        "tareas": [],
        "colaboradores": [asdict(c) for c in _colaboradores(ahora)],
        "historial_desempeno": [asdict(r) for r in _historial_desempeno(ahora)],
        "historial": [],
        "tratamientos": [],
        "meta": {
            "contadores": {"casos": 1057, "avisos": 103, "colaboradores": 8},
            "cargado_en": a_iso(ahora),
            "ultimo_escaneo": None,
        },
    }
