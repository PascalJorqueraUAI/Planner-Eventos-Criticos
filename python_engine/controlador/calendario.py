"""
Hora de Chile y plazos en horas hábiles.

Hora: el motor toma la hora oficial de Chile (America/Santiago), no la del servidor.
Así un servidor en la nube (que suele correr en UTC) no corre los plazos 3 o 4 horas.
Todas las fechas del repositorio se guardan como hora local de Chile sin zona.

Plazos: el SLA de una tarea cuenta solo horas hábiles (lunes a viernes, dentro del
horario laboral y fuera de los feriados de Chile). Una tarea de 4 h que llega un
viernes a las 17:00 vence el lunes siguiente a las 12:00, o el martes si el lunes es
feriado. Con PLAZOS_HABILES="no" se vuelve a contar en horas corridas.

Configuración (.env): ZONA_HORARIA, HORARIO_HABIL ("09:00-18:00"), PLAZOS_HABILES
("si"/"no") y FERIADOS_ADICIONALES ("2026-12-31,2027-01-02").
"""

import os
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import FrozenSet, Optional

from modelo.feriados import FERIADOS_CHILE

ZONA_POR_DEFECTO = "America/Santiago"
HORARIO_POR_DEFECTO = "09:00-18:00"
DIAS_HABILES = (0, 1, 2, 3, 4)     # lunes a viernes


# --- Hora de Chile ----------------------------------------------------------------------

def _offset_chile(utc: datetime) -> timedelta:
    """
    Respaldo si el equipo no tiene la base de zonas horarias (paquete tzdata en Windows).
    Regla vigente: horario de verano (UTC-3) desde el primer sábado de septiembre a las 24:00
    hasta el primer sábado de abril a las 24:00; el resto del año, UTC-4.
    """
    def primer_domingo(mes: int) -> date:
        inicio = date(utc.year, mes, 1)
        return inicio + timedelta(days=(6 - inicio.weekday()) % 7)

    fin_verano = datetime.combine(primer_domingo(4), time(3))      # 00:00 UTC-3 = 03:00 UTC
    inicio_verano = datetime.combine(primer_domingo(9), time(4))   # 00:00 UTC-4 = 04:00 UTC
    en_verano = utc < fin_verano or utc >= inicio_verano
    return timedelta(hours=-3 if en_verano else -4)


def ahora_chile() -> datetime:
    """Hora local de Chile, sin zona (el formato que usa todo el repositorio)."""
    utc = datetime.now(timezone.utc)
    nombre = os.environ.get("ZONA_HORARIA") or ZONA_POR_DEFECTO
    try:
        from zoneinfo import ZoneInfo
        local = utc.astimezone(ZoneInfo(nombre))
    except Exception:  # sin tzdata: se aplica la regla de Chile
        local = utc + _offset_chile(utc.replace(tzinfo=None))
    return local.replace(tzinfo=None, microsecond=0)


# --- Calendario hábil -------------------------------------------------------------------

def _hora(texto: str) -> time:
    horas, minutos = texto.strip().split(":")
    return time(int(horas), int(minutos))


@dataclass(frozen=True)
class Calendario:
    habil: bool = True
    inicio: time = time(9, 0)
    fin: time = time(18, 0)
    feriados: FrozenSet[date] = field(default_factory=lambda: frozenset(FERIADOS_CHILE))

    @classmethod
    def desde_entorno(cls) -> "Calendario":
        habil = (os.environ.get("PLAZOS_HABILES") or "si").strip().lower() not in ("no", "false", "0")
        inicio, fin = (os.environ.get("HORARIO_HABIL") or HORARIO_POR_DEFECTO).split("-")
        adicionales = {
            date.fromisoformat(d.strip()) for d in (os.environ.get("FERIADOS_ADICIONALES") or "").split(",") if d.strip()
        }
        calendario = cls(habil=habil, inicio=_hora(inicio), fin=_hora(fin),
                         feriados=frozenset(FERIADOS_CHILE) | frozenset(adicionales))
        if calendario.fin <= calendario.inicio:
            raise ValueError(f"HORARIO_HABIL inválido: {inicio}-{fin}")
        return calendario

    def dia_habil(self, dia: date) -> bool:
        return dia.weekday() in DIAS_HABILES and dia not in self.feriados

    def en_horario(self, momento: datetime) -> bool:
        return self.dia_habil(momento.date()) and self.inicio <= momento.time() < self.fin

    def _siguiente_apertura(self, momento: datetime) -> datetime:
        """El primer instante hábil desde `momento` (él mismo si ya lo es)."""
        dia = momento.date()
        if self.dia_habil(dia) and momento.time() < self.fin:
            return max(momento, datetime.combine(dia, self.inicio))
        dia += timedelta(days=1)
        while not self.dia_habil(dia):
            dia += timedelta(days=1)
        return datetime.combine(dia, self.inicio)

    def sumar_horas(self, desde: datetime, horas: float) -> datetime:
        """El instante en que se cumplen `horas` hábiles contadas desde `desde`."""
        if not self.habil:
            return desde + timedelta(hours=horas)
        restante = timedelta(hours=horas)
        cursor = self._siguiente_apertura(desde)
        while True:
            cierre = datetime.combine(cursor.date(), self.fin)
            if cursor + restante <= cierre:
                return cursor + restante
            restante -= cierre - cursor
            cursor = self._siguiente_apertura(cierre)

    def horas_entre(self, desde: datetime, hasta: datetime) -> float:
        """Horas hábiles transcurridas entre dos instantes (la operación inversa de `sumar_horas`)."""
        if not self.habil:
            return max(0.0, (hasta - desde).total_seconds() / 3600)
        total = timedelta()
        dia = desde.date()
        while dia <= hasta.date():
            if self.dia_habil(dia):
                inicio = max(desde, datetime.combine(dia, self.inicio))
                fin = min(hasta, datetime.combine(dia, self.fin))
                if fin > inicio:
                    total += fin - inicio
            dia += timedelta(days=1)
        return total.total_seconds() / 3600

    def publico(self, hoy: date) -> dict:
        return {
            "habiles": self.habil,
            "horario": f"{self.inicio:%H:%M}-{self.fin:%H:%M}",
            "zona": os.environ.get("ZONA_HORARIA") or ZONA_POR_DEFECTO,
            "proximos_feriados": [
                {"fecha": d.isoformat(), "nombre": FERIADOS_CHILE.get(d, "Feriado adicional")}
                for d in sorted(self.feriados) if d >= hoy
            ][:5],
        }

    def describir(self, horas: float) -> str:
        return f"{horas:g} h hábiles" if self.habil else f"{horas:g} h"


_vigente: Optional[Calendario] = None


def calendario() -> Calendario:
    """Calendario configurado en el entorno (se lee una vez por proceso)."""
    global _vigente
    if _vigente is None:
        _vigente = Calendario.desde_entorno()
    return _vigente


def usar(nuevo: Optional[Calendario]) -> None:
    """Fija el calendario (pruebas y simulaciones); None vuelve a leer el entorno."""
    global _vigente
    _vigente = nuevo
