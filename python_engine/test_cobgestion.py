"""
Unit Tests para el sistema de Cobgestion en Python
Ejecutable con: python3 -m unittest test_cobgestion.py
"""

import unittest
from datetime import datetime
from models import (
    Caso,
    Deudor,
    BienGarantia,
    AvisoPago,
    DatosExtraidos,
    COSTO_INCAUTACION_PREVENIDO_CLP,
)
from detector_eventos import DetectorEventosCriticos
from conciliador_mandantes import ConciliadorMandantes

class TestCobgestionEngine(unittest.TestCase):
    def setUp(self):
        # Caso real representativo: Cobranza vehicular con orden de incautación
        self.caso_vehicular = Caso(
            id="CASO-1052",
            rol_causa="C-1420-2026",
            tribunal="17° Juzgado Civil de Santiago",
            deudor=Deudor(
                nombre="Carlos Silva Mendoza",
                rut="16.482.910-K",
                email="carlos.silva@empresa.cl",
                telefono="+56 9 8831 2290"
            ),
            mandante="Forum Servicios Financieros",
            monto_deuda_total=4850000,
            monto_demandado=4850000,
            bien_en_garantia=BienGarantia(
                tipo="Vehículo",
                descripcion="Automóvil Suzuki Swift 1.2 GLX",
                patente="BB-CL-44",
                valor_aprox_clp=6500000
            ),
            estado_comercial="En negociación",
            estado_judicial="Orden de incautación vigente",
            responsable_comercial="Camila Valenzuela",
            responsable_judicial="Abg. Rodrigo Morales",
            fecha_creacion="2026-09-10T09:00:00"
        )

        self.aviso_pago = AvisoPago(
            id="AVP-801",
            caso_id="CASO-1052",
            fecha_recepcion="2026-10-23T08:30:00",
            monto_informado=850000,
            origen="Pantallazo cliente (WhatsApp)",
            canal="WhatsApp",
            estado_verificacion="informado",
            datos_extraidos=DatosExtraidos(
                banco_origen="Banco de Chile",
                banco_destino="Banco Santander",
                numero_operacion="TRF-8849102",
                rut_depositante="16.482.910-K",
                nombre_depositante="Carlos Silva M.",
                fecha_hora_operacion="2026-10-23 08:15",
                confianza_ia=0.98
            )
        )

    def test_deteccion_inmediata_aviso_pago(self):
        """Verifica que un comprobante informado genera Evento Crítico y Alerta Judicial de inmediato"""
        evento, t_com, t_jud = DetectorEventosCriticos.evaluar_aviso_pago(
            self.caso_vehicular,
            self.aviso_pago,
            "2026-10-23T08:31:00"
        )
        self.assertIsNotNone(evento)
        self.assertEqual(evento.tipo, "Pago informado pendiente de verificación")
        self.assertTrue(evento.alerta_judicial_generada)
        self.assertEqual(t_com.area, "Comercial")
        self.assertEqual(t_jud.area, "Judicial")
        self.assertEqual(t_com.estado, "Pendiente")
        self.assertEqual(t_jud.estado, "Pendiente")

    def test_alerta_critica_riesgo_incautacion_vehiculo_600k(self):
        """Verifica que el caso vehicular con orden de incautación active prioridad CRITICA y riesgo de 600.000 CLP"""
        evento, _, t_jud = DetectorEventosCriticos.evaluar_aviso_pago(
            self.caso_vehicular,
            self.aviso_pago
        )
        self.assertEqual(evento.prioridad, "CRITICA")
        self.assertEqual(evento.riesgo_financiero_clp, COSTO_INCAUTACION_PREVENIDO_CLP)
        self.assertIn("4 horas", t_jud.plazo_limite)
        self.assertIn("URGENTE: Suspender orden de incautación", t_jud.titulo)

    def test_regla_cierre_coordinado_bloqueo_si_falta_judicial(self):
        """
        Regla clave de Cobgestion:
        Si Comercial confirma el pago pero Judicial NO ha suspendido la causa,
        el evento NO puede cerrarse para evitar la pérdida de los $600.000 de incautación indebida.
        """
        evento, t_com, t_jud = DetectorEventosCriticos.evaluar_aviso_pago(
            self.caso_vehicular,
            self.aviso_pago
        )

        # Comercial resuelve y confirma pago
        DetectorEventosCriticos.aplicar_resolucion_comercial(
            evento,
            t_com,
            self.aviso_pago,
            nuevo_estado_pago="confirmado",
            usuario="Camila Valenzuela",
            observaciones="Transferencia verificada contra cartola Santander."
        )

        # Verificar que la tarea comercial está completada pero la judicial sigue pendiente
        self.assertEqual(t_com.estado, "Completada")
        self.assertEqual(t_jud.estado, "Pendiente")

        # Intentar cerrar el evento
        puede_cerrar, motivo = DetectorEventosCriticos.validar_cierre_evento(evento, t_com, t_jud)
        self.assertFalse(puede_cerrar)
        self.assertIn("Judicial aún no suspende", motivo)

    def test_cierre_exitoso_coordinado_ambas_areas(self):
        """Verifica que cuando ambas áreas completan sus tareas, el evento se cierra exitosamente"""
        evento, t_com, t_jud = DetectorEventosCriticos.evaluar_aviso_pago(
            self.caso_vehicular,
            self.aviso_pago
        )

        # Comercial confirma
        DetectorEventosCriticos.aplicar_resolucion_comercial(
            evento,
            t_com,
            self.aviso_pago,
            nuevo_estado_pago="confirmado",
            usuario="Camila Valenzuela",
            observaciones="Transferencia confirmada."
        )

        # Judicial suspende preventivamente y frena receptor
        DetectorEventosCriticos.aplicar_resolucion_judicial(
            evento,
            t_jud,
            self.caso_vehicular,
            accion="Suspender tramitación de incautación",
            escrito_presentado=True,
            usuario="Abg. Rodrigo Morales",
            observaciones="Notificado receptor don Mario Pezoa. Diligencia de incautación del auto BB-CL-44 suspendida."
        )

        self.assertEqual(self.caso_vehicular.estado_judicial, "Suspendido preventivo por aviso de pago")

        puede_cerrar, motivo = DetectorEventosCriticos.validar_cierre_evento(evento, t_com, t_jud)
        self.assertTrue(puede_cerrar)
        self.assertIn("coordinada", motivo)

    def test_conciliacion_lote_mandante(self):
        """Verifica conciliación masiva con planilla estructurada del mandante"""
        registros_mandante = [
            {
                "rut": "16.482.910-K",
                "monto": 850000,
                "codigo_operacion": "TRF-8849102",
                "fecha_pago": "2026-10-23",
                "mandante": "Forum Servicios Financieros"
            }
        ]

        resultado = ConciliadorMandantes.conciliar_lote(
            avisos=[self.aviso_pago],
            registros_mandante=registros_mandante
        )

        self.assertEqual(resultado["conciliados_exitosos"], 1)
        self.assertEqual(self.aviso_pago.estado_verificacion, "confirmado")

if __name__ == "__main__":
    unittest.main()
