"""Fixtures compartidas: un servicio en memoria con reloj controlado."""

from datetime import datetime, timedelta

from controlador.extraccion import ConfigExtraccion
from controlador.servicio import Servicio
from modelo.repositorio import Repositorio

AHORA = datetime(2026, 10, 26, 9, 0, 0)


class Reloj:
    def __init__(self, inicio: datetime = AHORA):
        self.momento = inicio

    def __call__(self) -> datetime:
        return self.momento

    def avanzar(self, **kw) -> None:
        self.momento += timedelta(**kw)


def servicio_de_prueba(reloj: Reloj = None, escenario: str = "base") -> Servicio:
    """
    Servicio con los datos del sandbox ya cargados y el primer escaneo ejecutado.
    Por defecto usa el escenario "base" (6 casos, 8 colaboradores), sobre el que están
    escritas las pruebas originales; test_escenario_ampliado.py usa el "ampliado".
    """
    # Gemini desactivado: las pruebas nunca dependen de variables de entorno ni de la red.
    sin_gemini = ConfigExtraccion(api_key="", modelo="sin-modelo", autorizado=False)
    return Servicio(Repositorio(ruta=None), reloj=reloj or Reloj(), config_extraccion=sin_gemini, escenario=escenario)


def tareas_del_caso(servicio: Servicio, caso_id: str, codigo: str):
    evento = next(e for e in servicio.repo.filtrar("eventos", caso_id=caso_id) if e["codigo"] == codigo)
    tareas = servicio.repo.filtrar("tareas", evento_id=evento["id"])
    return evento, {t["area"]: t for t in tareas}
