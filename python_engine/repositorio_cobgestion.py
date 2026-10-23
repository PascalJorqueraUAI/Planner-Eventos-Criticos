"""
Repositorio Centralizado de Cobgestion
Maneja las estructuras de datos especificadas para Cobgestion:
1. Casos
2. Avisos_Pago
3. Pagos_Conciliados
4. Eventos_Criticos
5. Tareas
6. Historial
Soporta persistencia en JSON, exportación a CSV (formato Excel) y consultas de auditoría.
"""

import json
import os
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
from models import (
    Caso,
    Deudor,
    BienGarantia,
    AvisoPago,
    DatosExtraidos,
    ArchivoComprobante,
    EventoCritico,
    TareaParalela,
    PagoConciliado,
    AuditoriaHistorial,
    ResolucionComercial,
    ResolucionJudicial,
    COSTO_INCAUTACION_PREVENIDO_CLP,
)
from detector_eventos import DetectorEventosCriticos

DATA_FILE = os.path.join(os.path.dirname(__file__), "data_store.json")

def _init_default_data() -> Dict[str, Any]:
    """Crea los datos iniciales incluyendo el caso real del vehículo de Cobgestion"""
    casos = [
        {
            "id": "CASO-1052",
            "rol_causa": "C-1420-2026",
            "tribunal": "17° Juzgado Civil de Santiago",
            "deudor": {
                "nombre": "Carlos Silva Mendoza",
                "rut": "16.482.910-K",
                "email": "carlos.silva@empresa.cl",
                "telefono": "+56 9 8831 2290",
                "direccion": "Av. Las Condes 10420, Depto 402, Las Condes"
            },
            "mandante": "Forum Servicios Financieros",
            "monto_deuda_total": 4850000,
            "monto_demandado": 4850000,
            "bien_en_garantia": {
                "tipo": "Vehículo",
                "descripcion": "Automóvil Suzuki Swift 1.2 GLX Año 2021",
                "patente": "BB-CL-44",
                "valor_aprox_clp": 6500000
            },
            "estado_comercial": "En negociación",
            "estado_judicial": "Orden de incautación vigente",
            "responsable_comercial": "Camila Valenzuela",
            "responsable_judicial": "Abg. Rodrigo Morales",
            "fecha_creacion": "2026-09-10T09:00:00",
            "fecha_diligencia_inminente": "2026-10-24T10:30:00"
        },
        {
            "id": "CASO-1053",
            "rol_causa": "C-8891-2025",
            "tribunal": "2° Juzgado de Letras de San Bernardo",
            "deudor": {
                "nombre": "María José Contreras Pinto",
                "rut": "18.291.433-2",
                "email": "mjcontreras@gmail.com",
                "telefono": "+56 9 9120 4451",
                "direccion": "Los Maitenes 412, San Bernardo"
            },
            "mandante": "Banco Santander Chile",
            "monto_deuda_total": 2300000,
            "monto_demandado": 2300000,
            "bien_en_garantia": {
                "tipo": "Bienes Muebles",
                "descripcion": "Mobiliario general y artefactos",
                "valor_aprox_clp": 1200000
            },
            "estado_comercial": "Acuerdo vigente",
            "estado_judicial": "Mandamiento de embargo",
            "responsable_comercial": "Ignacio Rivas",
            "responsable_judicial": "Abg. Valentina Tapia",
            "fecha_creacion": "2026-08-15T11:00:00"
        },
        {
            "id": "CASO-1054",
            "rol_causa": "C-3042-2026",
            "tribunal": "7° Juzgado Civil de Santiago",
            "deudor": {
                "nombre": "Transportes San Cristóbal SpA",
                "rut": "77.194.882-5",
                "email": "contacto@transsancristobal.cl",
                "telefono": "+56 2 2841 9900",
                "direccion": "Camino Melipilla 8830, Maipú"
            },
            "mandante": "Scotiabank Chile",
            "monto_deuda_total": 12800000,
            "monto_demandado": 12800000,
            "bien_en_garantia": {
                "tipo": "Vehículo",
                "descripcion": "Camión Tolva Mercedes-Benz Actros",
                "patente": "KR-WP-19",
                "valor_aprox_clp": 28000000
            },
            "estado_comercial": "Convenio incumplido",
            "estado_judicial": "Diligencia con receptor programada",
            "responsable_comercial": "Camila Valenzuela",
            "responsable_judicial": "Abg. Rodrigo Morales",
            "fecha_creacion": "2026-07-01T10:00:00",
            "fecha_diligencia_inminente": "2026-10-25T14:00:00"
        },
        {
            "id": "CASO-1055",
            "rol_causa": "C-1102-2026",
            "tribunal": "1° Juzgado Civil de Valparaíso",
            "deudor": {
                "nombre": "Gonzalo Patricio Alarcón",
                "rut": "15.772.304-1",
                "email": "g.alarcon@gmail.com",
                "telefono": "+56 9 7721 8891",
                "direccion": "Calle Prat 491, Valparaíso"
            },
            "mandante": "Banco Falabella",
            "monto_deuda_total": 980000,
            "monto_demandado": 980000,
            "bien_en_garantia": {
                "tipo": "Sin garantía",
                "descripcion": "Crédito de consumo sin caución específica",
                "valor_aprox_clp": 0
            },
            "estado_comercial": "Sin contacto",
            "estado_judicial": "Notificado",
            "responsable_comercial": "Ignacio Rivas",
            "responsable_judicial": "Abg. Valentina Tapia",
            "fecha_creacion": "2026-10-01T08:00:00"
        }
    ]

    # Aviso de pago real de ejemplo para el caso 1052
    avisos = [
        {
            "id": "AVP-101",
            "caso_id": "CASO-1052",
            "fecha_recepcion": "2026-10-23T06:15:00",
            "monto_informado": 850000,
            "origen": "Pantallazo cliente (WhatsApp)",
            "canal": "WhatsApp",
            "estado_verificacion": "informado",
            "datos_extraidos": {
                "banco_origen": "Banco de Chile",
                "banco_destino": "Banco Santander (Cobgestion / Forum)",
                "numero_operacion": "TRF-8849102",
                "rut_depositante": "16.482.910-K",
                "nombre_depositante": "Carlos Silva Mendoza",
                "fecha_hora_operacion": "2026-10-23 06:10",
                "comentario": "Pago de cuota y levantamiento de encargo de auto patente BB-CL-44",
                "confianza_ia": 0.98
            },
            "archivo_comprobante": {
                "nombre": "comprobante_transferencia_bancochile_carlos_silva.jpg",
                "tipo": "image",
                "preview_text": "Banco de Chile - Comprobante de Transferencia exitosa por $850.000 CLP a Forum Ref: Cuota Convenio Auto BB-CL-44"
            },
            "observaciones_comerciales": "Comprobante recibido por WhatsApp. Pendiente de conciliar contra cartola bancaria.",
            "observaciones_judiciales": "ALERTA: Diligencia de incautación programada para mañana. Se requiere suspensión inmediata para evitar costas de $600.000 CLP."
        }
    ]

    eventos = [
        {
            "id": "EVT-801",
            "caso_id": "CASO-1052",
            "aviso_pago_id": "AVP-101",
            "tipo": "Pago informado pendiente de verificación",
            "fecha_deteccion": "2026-10-23T06:15:30",
            "prioridad": "CRITICA",
            "estado": "En gestión paralela",
            "alerta_judicial_generada": True,
            "alerta_comercialGenerada": True,
            "riesgo_financiero_clp": COSTO_INCAUTACION_PREVENIDO_CLP,
            "cerrado": False
        }
    ]

    tareas = [
        {
            "id": "TSK-COM-801",
            "evento_critico_id": "EVT-801",
            "caso_id": "CASO-1052",
            "area": "Comercial",
            "titulo": "Verificar comprobante y conciliar pago",
            "descripcion": "Verificar comprobante #AVP-101 por $850.000 CLP informado vía WhatsApp contra cartola bancaria o planilla de Forum Servicios Financieros.",
            "responsable": "Camila Valenzuela",
            "fecha_creacion": "2026-10-23T06:15:30",
            "plazo_limite": "24 horas",
            "estado": "Pendiente"
        },
        {
            "id": "TSK-JUD-801",
            "evento_critico_id": "EVT-801",
            "caso_id": "CASO-1052",
            "area": "Judicial",
            "titulo": "URGENTE: Suspender orden de incautación de vehículo / embargo",
            "descripcion": "ALERTA PREVENTIVA: Se informó comprobante por $850.000 CLP. La causa C-1420-2026 (17° Juzgado Civil de Santiago) tiene orden de incautación vigente sobre Suzuki Swift patente BB-CL-44. Coordinar con receptor judicial inmediatamente para evitar pérdida de $600.000 CLP.",
            "responsable": "Abg. Rodrigo Morales",
            "fecha_creacion": "2026-10-23T06:15:30",
            "plazo_limite": "4 horas (URGENTE)",
            "estado": "Pendiente"
        }
    ]

    pagos_conciliados = [
        {
            "id": "CONC-9001",
            "caso_id": "CASO-1053",
            "aviso_pago_id": "AVP-HIST-09",
            "monto_conciliado": 450000,
            "codigo_planilla_mandante": "LIQ-SAN-2026-09",
            "mandante": "Banco Santander Chile",
            "fecha_liquidacion": "2026-09-30",
            "fecha_conciliacion": "2026-10-02T14:30:00",
            "conciliado_por": "Ignacio Rivas",
            "notas": "Liquidación mensual Santander conciliada con cuota acordada."
        }
    ]

    historial = [
        {
            "id": "LOG-1",
            "caso_id": "CASO-1052",
            "evento_critico_id": "EVT-801",
            "timestamp": "2026-10-23T06:15:00",
            "usuario": "Sistema Ingesta WhatsApp",
            "area": "Sistema IA",
            "accion": "Recepción de Comprobante No Estructurado",
            "detalles": "Ingreso de pantallazo de transferencia bancaria por $850.000 CLP. Extracción de datos con Gemini AI."
        },
        {
            "id": "LOG-2",
            "caso_id": "CASO-1052",
            "evento_critico_id": "EVT-801",
            "timestamp": "2026-10-23T06:15:30",
            "usuario": "Motor Python Cobgestion",
            "area": "Sistema IA",
            "accion": "Generación de Evento Crítico y Alerta Judicial",
            "detalles": "Regla activada: Aviso en estado 'informado' sobre causa con orden de incautación activa. Tarea judicial asignada con SLA de 4 horas para prevenir pérdida de $600.000 CLP."
        }
    ]

    return {
        "casos": casos,
        "avisos": avisos,
        "eventos": eventos,
        "tareas": tareas,
        "pagos_conciliados": pagos_conciliados,
        "historial": historial
    }

class RepositorioCobgestion:
    def __init__(self, filepath: str = DATA_FILE):
        self.filepath = filepath
        self.data = self.cargar_datos()

    def cargar_datos(self) -> Dict[str, Any]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        data = _init_default_data()
        self.guardar_datos(data)
        return data

    def guardar_datos(self, data: Optional[Dict[str, Any]] = None) -> None:
        if data is not None:
            self.data = data
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def registrar_aviso_y_detectar(self, aviso_dict: Dict[str, Any], usuario: str = "Ejecutivo") -> Dict[str, Any]:
        now = datetime.now().isoformat()
        caso_id = aviso_dict.get("caso_id")
        caso_raw = next((c for c in self.data["casos"] if c["id"] == caso_id), None)
        if not caso_raw:
            raise ValueError(f"Caso {caso_id} no existe")

        # Convertir a objetos para el detector
        deudor = Deudor(**caso_raw["deudor"])
        bien = BienGarantia(**caso_raw["bien_en_garantia"])
        caso_obj = Caso(
            id=caso_raw["id"],
            rol_causa=caso_raw["rol_causa"],
            tribunal=caso_raw["tribunal"],
            deudor=deudor,
            mandante=caso_raw["mandante"],
            monto_deuda_total=caso_raw["monto_deuda_total"],
            monto_demandado=caso_raw["monto_demandado"],
            bien_en_garantia=bien,
            estado_comercial=caso_raw["estado_comercial"],
            estado_judicial=caso_raw["estado_judicial"],
            responsable_comercial=caso_raw["responsable_comercial"],
            responsable_judicial=caso_raw["responsable_judicial"],
            fecha_creacion=caso_raw["fecha_creacion"],
            fecha_diligencia_inminente=caso_raw.get("fecha_diligencia_inminente")
        )

        datos_ext = DatosExtraidos(**aviso_dict.get("datos_extraidos", {}))
        archivo_raw = aviso_dict.get("archivo_comprobante")
        archivo = ArchivoComprobante(**archivo_raw) if archivo_raw else None

        aviso_obj = AvisoPago(
            id=aviso_dict.get("id", f"AVP-{str(len(self.data['avisos']) + 101)}"),
            caso_id=caso_id,
            fecha_recepcion=aviso_dict.get("fecha_recepcion", now),
            monto_informado=int(aviso_dict.get("monto_informado", 0)),
            origen=aviso_dict.get("origen", "Pantallazo cliente (WhatsApp)"),
            canal=aviso_dict.get("canal", "WhatsApp"),
            estado_verificacion="informado",
            datos_extraidos=datos_ext,
            archivo_comprobante=archivo,
            observaciones_comerciales=aviso_dict.get("observaciones_comerciales", ""),
            observaciones_judiciales=aviso_dict.get("observaciones_judiciales", "")
        )

        # Ejecutar detector en Python
        evento_obj, t_com_obj, t_jud_obj = DetectorEventosCriticos.evaluar_aviso_pago(caso_obj, aviso_obj, now)

        # Guardar en repositorio
        from dataclasses import asdict
        aviso_dict_full = asdict(aviso_obj)
        evento_dict_full = asdict(evento_obj)
        t_com_dict_full = asdict(t_com_obj)
        t_jud_dict_full = asdict(t_jud_obj)

        self.data["avisos"].insert(0, aviso_dict_full)
        self.data["eventos"].insert(0, evento_dict_full)
        self.data["tareas"].insert(0, t_com_dict_full)
        self.data["tareas"].insert(0, t_jud_dict_full)

        # Registrar historial de auditoría
        self.data["historial"].insert(0, {
            "id": f"LOG-{len(self.data['historial']) + 1}",
            "caso_id": caso_id,
            "evento_critico_id": evento_obj.id,
            "timestamp": now,
            "usuario": usuario,
            "area": "Comercial",
            "accion": "Ingreso de Aviso de Pago",
            "detalles": f"Registrado aviso #{aviso_obj.id} por ${aviso_obj.monto_informado:,.0f} CLP vía {aviso_obj.canal}."
        })
        self.data["historial"].insert(0, {
            "id": f"LOG-{len(self.data['historial']) + 1}",
            "caso_id": caso_id,
            "evento_critico_id": evento_obj.id,
            "timestamp": now,
            "usuario": "Detector Python",
            "area": "Sistema IA",
            "accion": "Evento Crítico & Alertas Paralelas Generadas",
            "detalles": f"Evento {evento_obj.id} prioridad {evento_obj.prioridad}. Tareas paralelas Comercial y Judicial asignadas."
        })

        self.guardar_datos()
        return {
            "aviso": aviso_dict_full,
            "evento": evento_dict_full,
            "tarea_comercial": t_com_dict_full,
            "tarea_judicial": t_jud_dict_full
        }

    def resolver_tarea_judicial(self, evento_id: str, accion: str, escrito: bool, usuario: str, notas: str) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        evento = next((e for e in self.data["eventos"] if e["id"] == evento_id), None)
        if not evento:
            raise ValueError(f"Evento {evento_id} no encontrado")

        tarea_jud = next((t for t in self.data["tareas"] if t["evento_critico_id"] == evento_id and t["area"] == "Judicial"), None)
        if not tarea_jud:
            raise ValueError("Tarea judicial no encontrada")

        caso = next((c for c in self.data["casos"] if c["id"] == evento["caso_id"]), None)

        if accion in ['Suspender tramitación de incautación', 'Notificar receptor judicial', 'Levantar encargo judicial']:
            if caso:
                caso["estado_judicial"] = "Suspendido preventivo por aviso de pago"

        tarea_jud["estado"] = "Completada"
        tarea_jud["resolucion"] = f"Acción: {accion}. Escrito: {'Sí' if escrito else 'No'}. {notas}"
        tarea_jud["fecha_resolucion"] = now

        evento["resolucion_judicial"] = {
            "fecha": now,
            "usuario": usuario,
            "accion_ejecutada": accion,
            "escrito_presentado": escrito,
            "observaciones": notas
        }

        # Comprobar si ambas están completas para cerrar
        tarea_com = next((t for t in self.data["tareas"] if t["evento_critico_id"] == evento_id and t["area"] == "Comercial"), None)
        if tarea_com and (tarea_com["estado"] == "Completada" or evento.get("resolucion_comercial")):
            evento["cerrado"] = True
            evento["estado"] = "Cerrado coordinado"
            evento["fecha_cierre"] = now

        self.data["historial"].insert(0, {
            "id": f"LOG-{len(self.data['historial']) + 1}",
            "caso_id": evento["caso_id"],
            "evento_critico_id": evento_id,
            "timestamp": now,
            "usuario": usuario,
            "area": "Judicial",
            "accion": f"Resolución Judicial: {accion}",
            "detalles": f"Diligencia coordinada. {notas}"
        })

        self.guardar_datos()
        return {"evento": evento, "tarea_judicial": tarea_jud, "caso": caso}

    def resolver_tarea_comercial(self, evento_id: str, nuevo_estado_pago: str, usuario: str, notas: str) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        evento = next((e for e in self.data["eventos"] if e["id"] == evento_id), None)
        if not evento:
            raise ValueError(f"Evento {evento_id} no encontrado")

        tarea_com = next((t for t in self.data["tareas"] if t["evento_critico_id"] == evento_id and t["area"] == "Comercial"), None)
        if not tarea_com:
            raise ValueError("Tarea comercial no encontrada")

        aviso = next((a for a in self.data["avisos"] if a["id"] == evento.get("aviso_pago_id")), None)
        if aviso:
            aviso["estado_verificacion"] = nuevo_estado_pago
            aviso["observaciones_comerciales"] = notas

        tarea_com["estado"] = "Completada"
        tarea_com["resolucion"] = f"Pago {nuevo_estado_pago}. {notas}"
        tarea_com["fecha_resolucion"] = now

        evento["resolucion_comercial"] = {
            "fecha": now,
            "usuario": usuario,
            "estado_final_pago": nuevo_estado_pago,
            "observaciones": notas
        }

        if nuevo_estado_pago == 'observado':
            evento["tipo"] = "Pago observado con discrepancia"

        # Verificar regla Cobgestion: Solo cerrar si Judicial también resolvió!
        tarea_jud = next((t for t in self.data["tareas"] if t["evento_critico_id"] == evento_id and t["area"] == "Judicial"), None)
        if tarea_jud and (tarea_jud["estado"] == "Completada" or evento.get("resolucion_judicial")):
            evento["cerrado"] = True
            evento["estado"] = "Cerrado coordinado"
            evento["fecha_cierre"] = now

        self.data["historial"].insert(0, {
            "id": f"LOG-{len(self.data['historial']) + 1}",
            "caso_id": evento["caso_id"],
            "evento_critico_id": evento_id,
            "timestamp": now,
            "usuario": usuario,
            "area": "Comercial",
            "accion": f"Resolución Comercial: Pago {nuevo_estado_pago.upper()}",
            "detalles": f"Comprobante verificado. {notas}"
        })

        self.guardar_datos()
        return {"evento": evento, "tarea_comercial": tarea_com, "aviso": aviso}

    def exportar_csv(self, directorio_destino: str = ".") -> List[str]:
        """Exporta las 6 hojas requeridas para Cobgestion a CSV (compatibles con Excel)"""
        os.makedirs(directorio_destino, exist_ok=True)
        archivos = []

        # 1. Casos.csv
        casos_path = os.path.join(directorio_destino, "Cobgestion_Casos.csv")
        with open(casos_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Rol Causa", "Tribunal", "Deudor", "RUT", "Mandante", "Monto Deuda", "Bien Garantía", "Patente", "Estado Comercial", "Estado Judicial", "Resp. Comercial", "Resp. Judicial"])
            for c in self.data["casos"]:
                writer.writerow([
                    c["id"], c["rol_causa"], c["tribunal"], c["deudor"]["nombre"], c["deudor"]["rut"],
                    c["mandante"], c["monto_deuda_total"], c["bien_en_garantia"]["descripcion"],
                    c["bien_en_garantia"].get("patente", ""), c["estado_comercial"], c["estado_judicial"],
                    c["responsable_comercial"], c["responsable_judicial"]
                ])
        archivos.append(casos_path)

        # 2. Avisos_Pago.csv
        avisos_path = os.path.join(directorio_destino, "Cobgestion_Avisos_Pago.csv")
        with open(avisos_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID Aviso", "Caso ID", "Fecha Recepción", "Monto Informado", "Origen", "Canal", "Estado Verificación", "N° Operación", "Banco Origen", "Depositante", "Observaciones"])
            for a in self.data["avisos"]:
                ext = a.get("datos_extraidos", {})
                writer.writerow([
                    a["id"], a["caso_id"], a["fecha_recepcion"], a["monto_informado"], a["origen"],
                    a["canal"], a["estado_verificacion"], ext.get("numero_operacion", ""),
                    ext.get("banco_origen", ""), ext.get("nombre_depositante", ""), a.get("observaciones_comerciales", "")
                ])
        archivos.append(avisos_path)

        # 3. Eventos_Criticos.csv
        eventos_path = os.path.join(directorio_destino, "Cobgestion_Eventos_Criticos.csv")
        with open(eventos_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID Evento", "Caso ID", "Aviso ID", "Tipo Evento", "Fecha Detección", "Prioridad", "Estado", "Riesgo Financiero CLP", "Cerrado"])
            for e in self.data["eventos"]:
                writer.writerow([
                    e["id"], e["caso_id"], e.get("aviso_pago_id", ""), e["tipo"], e["fecha_deteccion"],
                    e["prioridad"], e["estado"], e.get("riesgo_financiero_clp", 0), "SÍ" if e.get("cerrado") else "NO"
                ])
        archivos.append(eventos_path)

        # 4. Tareas.csv
        tareas_path = os.path.join(directorio_destino, "Cobgestion_Tareas.csv")
        with open(tareas_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID Tarea", "Evento ID", "Caso ID", "Área", "Título", "Responsable", "Plazo", "Estado", "Resolución"])
            for t in self.data["tareas"]:
                writer.writerow([
                    t["id"], t["evento_critico_id"], t["caso_id"], t["area"], t["titulo"],
                    t["responsable"], t["plazo_limite"], t["estado"], t.get("resolucion", "")
                ])
        archivos.append(tareas_path)

        # 5. Pagos_Conciliados.csv
        conc_path = os.path.join(directorio_destino, "Cobgestion_Pagos_Conciliados.csv")
        with open(conc_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID Conciliación", "Caso ID", "Aviso ID", "Monto Conciliado", "Código Mandante", "Mandante", "Fecha Liquidación", "Conciliado Por"])
            for p in self.data["pagos_conciliados"]:
                writer.writerow([
                    p["id"], p["caso_id"], p.get("aviso_pago_id", ""), p["monto_conciliado"],
                    p["codigo_planilla_mandante"], p["mandante"], p["fecha_liquidacion"], p["conciliado_por"]
                ])
        archivos.append(conc_path)

        # 6. Historial.csv
        hist_path = os.path.join(directorio_destino, "Cobgestion_Historial.csv")
        with open(hist_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID Log", "Caso ID", "Timestamp", "Usuario", "Área", "Acción", "Detalles"])
            for h in self.data["historial"]:
                writer.writerow([
                    h["id"], h["caso_id"], h["timestamp"], h["usuario"], h["area"], h["accion"], h["detalles"]
                ])
        archivos.append(hist_path)

        return archivos
