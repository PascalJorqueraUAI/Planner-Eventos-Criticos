"""
Detector de Eventos Críticos para Cobgestion
Implementa la lógica del negocio requerida por Cobgestion:
1. Recepción de nuevo aviso de pago -> Generación inmediata de Evento Crítico y Alerta Judicial.
2. Detección de casos de alto riesgo (Vehículo con orden de incautación activa -> Prioridad CRÍTICA y riesgo 600.000 CLP).
3. Generación de dos tareas paralelas asignadas a los ejecutivos de cada área.
4. Regla de Cierre Coordinado: El evento no se cierra hasta que AMBAS áreas resuelvan.
"""

from datetime import datetime
import uuid
from typing import Tuple, Dict, Any, Optional, List
from models import (
    Caso,
    AvisoPago,
    EventoCritico,
    TareaParalela,
    ResolucionComercial,
    ResolucionJudicial,
    COSTO_INCAUTACION_PREVENIDO_CLP,
)

class DetectorEventosCriticos:
    @staticmethod
    def evaluar_aviso_pago(
        caso: Caso,
        aviso: AvisoPago,
        timestamp_actual: Optional[str] = None
    ) -> Tuple[EventoCritico, TareaParalela, TareaParalela]:
        """
        Regla central Cobgestion:
        Cuando se registra un nuevo aviso de pago asociado a un caso, se genera un
        evento crítico de tipo 'Pago informado pendiente de verificación'.
        No se espera a la conciliación definitiva para alertar a Judicial.
        """
        now = timestamp_actual or datetime.now().isoformat()
        
        # Evaluar riesgo judicial inminente
        estados_alto_riesgo = [
            'Orden de incautación vigente',
            'Diligencia con receptor programada',
            'Mandamiento de embargo'
        ]
        
        es_alto_riesgo = (
            caso.estado_judicial in estados_alto_riesgo or
            caso.bien_en_garantia.tipo == 'Vehículo'
        )
        
        prioridad = 'CRITICA' if es_alto_riesgo else 'ALTA'
        riesgo_financiero = COSTO_INCAUTACION_PREVENIDO_CLP if es_alto_riesgo else 0
        
        evento_id = f"EVT-{str(uuid.uuid4())[:8].upper()}"
        
        evento = EventoCritico(
            id=evento_id,
            caso_id=caso.id,
            aviso_pago_id=aviso.id,
            tipo='Pago informado pendiente de verificación',
            fecha_deteccion=now,
            prioridad=prioridad,
            estado='En gestión paralela',
            alerta_judicial_generada=True,
            alerta_comercialGenerada=True,
            riesgo_financiero_clp=riesgo_financiero,
            cerrado=False
        )
        
        # Tarea Comercial
        plazo_comercial = "24 horas"
        tarea_comercial = TareaParalela(
            id=f"TSK-COM-{str(uuid.uuid4())[:6].upper()}",
            evento_critico_id=evento_id,
            caso_id=caso.id,
            area='Comercial',
            titulo='Verificar comprobante y conciliar pago',
            descripcion=(
                f"Verificar comprobante #{aviso.id} por ${aviso.monto_informado:,.0f} CLP "
                f"informado vía {aviso.canal} contra cartola bancaria o planilla de {caso.mandante}."
            ),
            responsable=caso.responsable_comercial,
            fecha_creacion=now,
            plazo_limite=plazo_comercial,
            estado='Pendiente'
        )
        
        # Tarea Judicial
        if es_alto_riesgo:
            plazo_judicial = "4 horas (URGENTE)"
            patente_info = f" (Patente {caso.bien_en_garantia.patente})" if caso.bien_en_garantia.patente else ""
            titulo_judicial = "URGENTE: Suspender orden de incautación de vehículo / embargo"
            desc_judicial = (
                f"ALERTA PREVENTIVA: Se informó comprobante por ${aviso.monto_informado:,.0f} CLP. "
                f"La causa {caso.rol_causa} ({caso.tribunal}) tiene orden de incautación vigente sobre vehículo{patente_info}. "
                f"Coordinar inmediatamente con receptor judicial para frenar diligencia y evitar pérdida de $600.000 CLP en costas."
            )
        else:
            plazo_judicial = "24 horas"
            titulo_judicial = "Revisar estado procesal y evaluar suspensión"
            desc_judicial = (
                f"Analizar impacto del comprobante en causa {caso.rol_causa} ({caso.tribunal}). "
                f"Evaluar presentación de escrito preventivo de suspensión."
            )
            
        tarea_judicial = TareaParalela(
            id=f"TSK-JUD-{str(uuid.uuid4())[:6].upper()}",
            evento_critico_id=evento_id,
            caso_id=caso.id,
            area='Judicial',
            titulo=titulo_judicial,
            descripcion=desc_judicial,
            responsable=caso.responsable_judicial,
            fecha_creacion=now,
            plazo_limite=plazo_judicial,
            estado='Pendiente'
        )
        
        return evento, tarea_comercial, tarea_judicial

    @staticmethod
    def validar_cierre_evento(
        evento: EventoCritico,
        tarea_comercial: TareaParalela,
        tarea_judicial: TareaParalela
    ) -> Tuple[bool, str]:
        """
        Regla de oro de Cobgestion:
        El evento NO se cierra automáticamente cuando Comercial confirma el pago.
        Ambas áreas deben completar sus tareas o registrar una resolución válida.
        De lo contrario, tendríamos el pago conciliado pero la incautación del vehículo ejecutada.
        """
        comercial_ok = (
            tarea_comercial.estado == 'Completada' or
            evento.resolucion_comercial is not None
        )
        judicial_ok = (
            tarea_judicial.estado == 'Completada' or
            evento.resolucion_judicial is not None
        )
        
        if not comercial_ok and not judicial_ok:
            return False, "Ambas tareas (Comercial y Judicial) se encuentran pendientes."
            
        if comercial_ok and not judicial_ok:
            return False, (
                "Riesgo crítico: Comercial verificó el pago, pero Judicial aún no suspende "
                "la causa ni coordina con el receptor. El vehículo o bien podría ser incautado por error."
            )
            
        if not comercial_ok and judicial_ok:
            return False, (
                "Judicial suspendió la diligencia preventivamente, pero Comercial aún no confirma "
                "la conciliación del pago con el mandante."
            )
            
        return True, "Ambas áreas han resuelto sus tareas de manera coordinada."

    @staticmethod
    def aplicar_resolucion_comercial(
        evento: EventoCritico,
        tarea_comercial: TareaParalela,
        aviso: AvisoPago,
        nuevo_estado_pago: str,
        usuario: str,
        observaciones: str,
        timestamp: Optional[str] = None
    ) -> None:
        now = timestamp or datetime.now().isoformat()
        aviso.estado_verificacion = nuevo_estado_pago
        aviso.observaciones_comerciales = observaciones
        
        tarea_comercial.estado = 'Completada'
        tarea_comercial.resolucion = f"Pago marcado como {nuevo_estado_pago}. {observaciones}"
        tarea_comercial.fecha_resolucion = now
        
        evento.resolucion_comercial = ResolucionComercial(
            fecha=now,
            usuario=usuario,
            estado_final_pago=nuevo_estado_pago,
            observaciones=observaciones
        )
        
        if nuevo_estado_pago == 'observado':
            evento.tipo = 'Pago observado con discrepancia'

    @staticmethod
    def aplicar_resolucion_judicial(
        evento: EventoCritico,
        tarea_judicial: TareaParalela,
        caso: Caso,
        accion: str,
        escrito_presentado: bool,
        usuario: str,
        observaciones: str,
        timestamp: Optional[str] = None
    ) -> None:
        now = timestamp or datetime.now().isoformat()
        
        # Si se suspendió la incautación, actualizar estado judicial del caso
        if accion in ['Suspender tramitación de incautación', 'Notificar receptor judicial', 'Levantar encargo judicial']:
            caso.estado_judicial = 'Suspendido preventivo por aviso de pago'
            
        tarea_judicial.estado = 'Completada'
        tarea_judicial.resolucion = f"Acción: {accion}. Escrito: {'Sí' if escrito_presentado else 'No'}. {observaciones}"
        tarea_judicial.fecha_resolucion = now
        
        evento.resolucion_judicial = ResolucionJudicial(
            fecha=now,
            usuario=usuario,
            accion_ejecutada=accion,
            escrito_presentado=escrito_presentado,
            observaciones=observaciones
        )
