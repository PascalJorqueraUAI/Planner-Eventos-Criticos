"""
Feriados legales de Chile (capa Modelo).

Los plazos de las tareas no corren en estos días (ver controlador/calendario.py).
Fuente: calendario oficial publicado en https://www.feriados.cl y el Diario Oficial.
Se actualiza una vez al año; los feriados extraordinarios (elecciones, interferiados
decretados) se agregan con FERIADOS_ADICIONALES en el .env sin tocar el código.
"""

from datetime import date

FERIADOS_CHILE = {
    # 2026
    date(2026, 1, 1): "Año Nuevo",
    date(2026, 4, 3): "Viernes Santo",
    date(2026, 4, 4): "Sábado Santo",
    date(2026, 5, 1): "Día Nacional del Trabajo",
    date(2026, 5, 21): "Día de las Glorias Navales",
    date(2026, 6, 21): "Día Nacional de los Pueblos Indígenas",
    date(2026, 6, 29): "San Pedro y San Pablo",
    date(2026, 7, 16): "Día de la Virgen del Carmen",
    date(2026, 8, 15): "Asunción de la Virgen",
    date(2026, 9, 18): "Independencia Nacional",
    date(2026, 9, 19): "Día de las Glorias del Ejército",
    date(2026, 10, 12): "Encuentro de Dos Mundos",
    date(2026, 10, 31): "Día de las Iglesias Evangélicas y Protestantes",
    date(2026, 11, 1): "Día de Todos los Santos",
    date(2026, 12, 8): "Inmaculada Concepción",
    date(2026, 12, 25): "Navidad",
    # 2027 (verificar los trasladables contra el calendario oficial cuando se publique)
    date(2027, 1, 1): "Año Nuevo",
    date(2027, 3, 26): "Viernes Santo",
    date(2027, 3, 27): "Sábado Santo",
    date(2027, 5, 1): "Día Nacional del Trabajo",
    date(2027, 5, 21): "Día de las Glorias Navales",
    date(2027, 6, 21): "Día Nacional de los Pueblos Indígenas",
    date(2027, 6, 28): "San Pedro y San Pablo",
    date(2027, 7, 16): "Día de la Virgen del Carmen",
    date(2027, 8, 15): "Asunción de la Virgen",
    date(2027, 9, 18): "Independencia Nacional",
    date(2027, 9, 19): "Día de las Glorias del Ejército",
    date(2027, 10, 11): "Encuentro de Dos Mundos",
    date(2027, 10, 31): "Día de las Iglesias Evangélicas y Protestantes",
    date(2027, 11, 1): "Día de Todos los Santos",
    date(2027, 12, 8): "Inmaculada Concepción",
    date(2027, 12, 25): "Navidad",
}
