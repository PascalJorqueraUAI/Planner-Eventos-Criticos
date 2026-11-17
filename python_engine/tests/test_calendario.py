import os
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest import mock

from controlador import calendario
from controlador.calendario import Calendario, _offset_chile, ahora_chile
from tests.utilidades import Reloj, servicio_de_prueba, tareas_del_caso

HABIL = Calendario()


class TestHorasHabiles(unittest.TestCase):
    def test_dentro_del_mismo_dia(self):
        self.assertEqual(HABIL.sumar_horas(datetime(2026, 11, 16, 10, 0), 4), datetime(2026, 11, 16, 14, 0))

    def test_viernes_en_la_tarde_vence_el_lunes(self):
        self.assertEqual(HABIL.sumar_horas(datetime(2026, 11, 13, 17, 0), 4), datetime(2026, 11, 16, 12, 0))

    def test_feriado_no_cuenta(self):
        # Viernes 9 de octubre; el lunes 12 es feriado (Encuentro de Dos Mundos).
        self.assertEqual(HABIL.sumar_horas(datetime(2026, 10, 9, 17, 0), 4), datetime(2026, 10, 13, 12, 0))
        # Martes 8 de diciembre (Inmaculada Concepción).
        self.assertEqual(HABIL.sumar_horas(datetime(2026, 12, 7, 16, 0), 4), datetime(2026, 12, 9, 11, 0))

    def test_antes_de_la_apertura_y_de_noche(self):
        self.assertEqual(HABIL.sumar_horas(datetime(2026, 11, 16, 7, 0), 2), datetime(2026, 11, 16, 11, 0))
        self.assertEqual(HABIL.sumar_horas(datetime(2026, 11, 16, 23, 0), 2), datetime(2026, 11, 17, 11, 0))
        self.assertEqual(HABIL.sumar_horas(datetime(2026, 11, 14, 12, 0), 1), datetime(2026, 11, 16, 10, 0))  # sábado

    def test_plazo_de_varios_dias(self):
        # 24 h hábiles = 2 jornadas de 9 h + 6 h.
        self.assertEqual(HABIL.sumar_horas(datetime(2026, 11, 16, 9, 0), 24), datetime(2026, 11, 18, 15, 0))

    def test_horas_habiles_entre_dos_instantes(self):
        # Viernes 17:00 → lunes 10:00: 1 h del viernes + 1 h del lunes.
        self.assertEqual(HABIL.horas_entre(datetime(2026, 11, 13, 17, 0), datetime(2026, 11, 16, 10, 0)), 2)
        # Pasando por el feriado del 8 de diciembre.
        self.assertEqual(HABIL.horas_entre(datetime(2026, 12, 7, 16, 0), datetime(2026, 12, 9, 11, 0)), 4)
        self.assertEqual(HABIL.horas_entre(datetime(2026, 11, 14, 10, 0), datetime(2026, 11, 15, 20, 0)), 0)

    def test_horas_entre_es_la_inversa_de_sumar_horas(self):
        desde = datetime(2026, 11, 12, 15, 30)
        for horas in (0.5, 4, 8, 24, 48):
            self.assertAlmostEqual(HABIL.horas_entre(desde, HABIL.sumar_horas(desde, horas)), horas)

    def test_horas_corridas(self):
        self.assertEqual(Calendario(habil=False).sumar_horas(datetime(2026, 11, 13, 17, 0), 4), datetime(2026, 11, 13, 21, 0))

    def test_configuracion_desde_el_entorno(self):
        entorno = {"HORARIO_HABIL": "08:30-17:30", "FERIADOS_ADICIONALES": "2026-11-17", "PLAZOS_HABILES": "si"}
        with mock.patch.dict(os.environ, entorno):
            cal = Calendario.desde_entorno()
        self.assertFalse(cal.dia_habil(date(2026, 11, 17)))
        self.assertEqual(cal.sumar_horas(datetime(2026, 11, 16, 16, 30), 2), datetime(2026, 11, 18, 9, 30))
        with mock.patch.dict(os.environ, {"PLAZOS_HABILES": "no"}):
            self.assertFalse(Calendario.desde_entorno().habil)


class TestHoraDeChile(unittest.TestCase):
    def test_respaldo_sin_tzdata_coincide_con_la_zona_oficial(self):
        try:
            from zoneinfo import ZoneInfo
            zona = ZoneInfo("America/Santiago")
        except Exception:
            self.skipTest("Sin base de zonas horarias en este equipo")
        instante = datetime(2026, 1, 1)
        while instante < datetime(2027, 12, 31):
            oficial = instante.replace(tzinfo=timezone.utc).astimezone(zona).utcoffset()
            self.assertEqual(_offset_chile(instante), oficial, instante)
            instante += timedelta(hours=7)

    def test_verano_e_invierno(self):
        self.assertEqual(_offset_chile(datetime(2026, 1, 15, 12)), timedelta(hours=-3))
        self.assertEqual(_offset_chile(datetime(2026, 7, 15, 12)), timedelta(hours=-4))

    def test_no_depende_de_la_zona_del_servidor(self):
        utc = datetime(2026, 7, 15, 16, 0)

        class RelojFijo(datetime):
            @classmethod
            def now(cls, tz=None):
                return utc.replace(tzinfo=tz)

        with mock.patch("controlador.calendario.datetime", RelojFijo):
            self.assertEqual(ahora_chile(), datetime(2026, 7, 15, 12, 0))


class TestPlazosDeLasTareas(unittest.TestCase):
    CASO = {
        "rol_causa": "C-7101-2026", "tribunal": "1° Juzgado Civil de Santiago", "deudor_nombre": "Ana Pérez Rojas",
        "deudor_rut": "12.345.678-5", "mandante": "Forum", "monto_deuda": "3000000", "bien_tipo": "Vehículo",
        "bien_descripcion": "Automóvil", "bien_patente": "ZZ-YY-11", "estado_comercial": "En negociación",
        "estado_judicial": "Orden de incautación vigente", "responsable_comercial": "COL-0003",
        "responsable_judicial": "COL-0007",
    }

    def setUp(self):
        # Viernes 13 de noviembre de 2026, 17:00: llega un comprobante con una incautación vigente.
        self.reloj = Reloj(datetime(2026, 11, 13, 17, 0))
        self.servicio = servicio_de_prueba(self.reloj)

    def crear(self, **extra):
        caso = self.servicio.crear_caso({**self.CASO, "fecha_diligencia": "", **extra}, {"monto": 500000}, "Gerencia")["caso"]
        return tareas_del_caso(self.servicio, caso["id"], "EC-01")[1]

    def test_critica_del_viernes_vence_el_lunes_en_horas_habiles(self):
        tareas = self.crear()
        self.assertEqual(tareas["Judicial"]["fecha_limite"], "2026-11-16T12:00:00")
        self.assertEqual(tareas["Judicial"]["plazo_detalle"], "4 h hábiles")

    def test_nunca_vence_despues_de_la_diligencia(self):
        tareas = self.crear(fecha_diligencia="2026-11-16T08:00")
        self.assertEqual(tareas["Judicial"]["fecha_limite"], "2026-11-16T06:00:00")
        self.assertIn("antes de la diligencia", tareas["Judicial"]["plazo_detalle"])

    def test_el_escalamiento_tambien_usa_horas_habiles(self):
        tareas = self.crear()
        self.reloj.momento = datetime(2026, 11, 16, 12, 30)
        self.servicio.escanear()
        judicial = self.servicio.repo.obtener("tareas", tareas["Judicial"]["id"])
        self.assertGreaterEqual(judicial["nivel_escalamiento"], 1)
        self.assertEqual(judicial["plazo_escalamiento"], "2026-11-16T14:30:00")   # la mitad: 2 h hábiles

    def tearDown(self):
        calendario.usar(Calendario())


if __name__ == "__main__":
    unittest.main()
