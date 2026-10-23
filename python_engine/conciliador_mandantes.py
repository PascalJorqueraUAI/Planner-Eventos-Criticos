"""
Módulo de Conciliación de Planillas Estructuradas de Mandantes
Permite comparar las planillas masivas de bancos/mandantes contra los
avisos de pago registrados en Cobgestion, actualizando estados y detectando discrepancias.
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime
import uuid
from models import AvisoPago, PagoConciliado, EventoCritico, TareaParalela

class ConciliadorMandantes:
    @staticmethod
    def conciliar_lote(
        avisos: List[AvisoPago],
        registros_mandante: List[Dict[str, Any]],
        usuario: str = "Sistema Batch Mandante",
        timestamp: str = None
    ) -> Dict[str, Any]:
        """
        Compara registros de planilla estructurada contra avisos de pago.
        Cada registro_mandante tiene: rut, monto, codigo_operacion, fecha_pago, mandante
        """
        now = timestamp or datetime.now().isoformat()
        conciliados: List[PagoConciliado] = []
        avisos_actualizados: List[AvisoPago] = []
        discrepancias: List[Dict[str, Any]] = []

        for reg in registros_mandante:
            rut_m = str(reg.get('rut', '')).replace('.', '').replace('-', '').upper()
            monto_m = int(reg.get('monto', 0))
            cod_op = str(reg.get('codigo_operacion', '')).strip().upper()
            mandante = reg.get('mandante', 'Mandante')

            # Buscar coincidencia entre avisos en estado 'informado' u 'observado'
            match = None
            for av in avisos:
                av_rut = str(av.datos_extraidos.rut_depositante or '').replace('.', '').replace('-', '').upper()
                av_op = str(av.datos_extraidos.numero_operacion or '').strip().upper()
                
                # Coincidencia por RUT y Monto, o por Número de Operación
                if (av_rut and av_rut == rut_m and av.monto_informado == monto_m) or (av_op and av_op == cod_op):
                    match = av
                    break

            if match:
                diff = match.monto_informado - monto_m
                if abs(diff) == 0:
                    match.estado_verificacion = 'confirmado'
                    match.observaciones_comerciales = (
                        f"Conciliado con planilla {mandante} (Operación {cod_op}) el {now[:10]}."
                    )
                    pago_conciliado = PagoConciliado(
                        id=f"CONC-{str(uuid.uuid4())[:6].upper()}",
                        caso_id=match.caso_id,
                        aviso_pago_id=match.id,
                        monto_conciliado=monto_m,
                        codigo_planilla_mandante=cod_op,
                        mandante=mandante,
                        fecha_liquidacion=reg.get('fecha_pago', now[:10]),
                        fecha_conciliacion=now,
                        conciliado_por=usuario,
                        notas="Conciliación automática exitosa sin diferencias."
                    )
                    conciliados.append(pago_conciliado)
                    avisos_actualizados.append(match)
                else:
                    match.estado_verificacion = 'observado'
                    match.observaciones_comerciales = (
                        f"Diferencia detectada en monto: Informado ${match.monto_informado:,.0f} vs Planilla ${monto_m:,.0f}."
                    )
                    discrepancias.append({
                        'aviso_id': match.id,
                        'caso_id': match.caso_id,
                        'monto_informado': match.monto_informado,
                        'monto_mandante': monto_m,
                        'diferencia': diff,
                        'mandante': mandante
                    })
                    avisos_actualizados.append(match)
            else:
                # Pago nuevo reportado directamente por mandante que no tenía aviso previo
                discrepancias.append({
                    'aviso_id': None,
                    'rut': reg.get('rut'),
                    'monto_mandante': monto_m,
                    'codigo_operacion': cod_op,
                    'mandante': mandante,
                    'tipo': 'Pago en planilla sin aviso previo del cliente'
                })

        return {
            'conciliados_exitosos': len(conciliados),
            'discrepancias_encontradas': len(discrepancias),
            'pagos_conciliados': conciliados,
            'avisos_actualizados': avisos_actualizados,
            'detalle_discrepancias': discrepancias
        }
