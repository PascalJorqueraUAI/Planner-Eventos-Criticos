"""
Riesgo de un evento crítico: lo que Cobgestion tendría que asumir si el apremio
sigue su curso sin que Judicial alcance a actuar, como en el caso real del auto.

Se estima con el contexto de cada caso:
  - la etapa del apremio: con retiro físico del bien (orden de incautación o
    diligencia con receptor) o solo embargo (mandamiento),
  - el bien: tipo y tamaño (una moto no se retira igual que un camión),
  - el monto de la deuda, del que dependen las costas personales.

Las tarifas son SUPUESTOS DE LA DEMO, calibrados para que el caso del auto
(CASO-1052: automóvil, orden de incautación, deuda de $4.850.000) se acerque a
los $600.000 que costó la incautación real. Cobgestion debe reemplazarlas por
sus costos efectivos; todas están en este archivo.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from modelo.entidades import ESTADOS_JUDICIALES_APREMIO

# Apremios en que el receptor retira físicamente el bien.
APREMIOS_CON_RETIRO = ("Orden de incautación vigente", "Diligencia con receptor programada")

HONORARIO_RECEPTOR_CLP = 120_000
DIAS_CUSTODIA = 15                      # hasta que se ordena y se ejecuta la devolución
PORCENTAJE_COSTAS = 0.03                # costas personales del incidente, sobre la deuda
COSTAS_MINIMAS_CLP = 50_000
COSTAS_MAXIMAS_CLP = 600_000


@dataclass(frozen=True)
class TarifaRetiro:
    medio: str
    retiro: int
    custodia_diaria: int
    devolucion: int


TARIFAS_RETIRO: Dict[str, TarifaRetiro] = {
    "liviano": TarifaRetiro("Grúa", 120_000, 10_000, 60_000),
    "moto": TarifaRetiro("Traslado en camioneta", 60_000, 5_000, 30_000),
    "pesado": TarifaRetiro("Grúa cama baja", 450_000, 25_000, 250_000),
    "muebles": TarifaRetiro("Flete y embalaje", 90_000, 6_000, 60_000),
}

# Embargo sin retiro de un bien inscrito: anotación y posterior alzamiento en el registro.
INSCRIPCION_ALZAMIENTO: Dict[str, Tuple[str, int]] = {
    "Vehículo": ("Anotación y alzamiento en el RVM", 35_000),
    "Inmueble": ("Inscripción y alzamiento en el CBR", 120_000),
}

# Palabras completas: "camioneta" contiene "camion" pero se retira con grúa normal.
PATRON_PESADO = re.compile(r"\b(cami[oó]n|tolva|tracto\w*|bus|\w*excavadora|gr[uú]a|cargador)\b")


def clase_bien(bien: Dict[str, Any]) -> str:
    """Clasifica el bien según cómo se retira: liviano, moto, pesado, muebles, inmueble o sin_garantia."""
    tipo, descripcion = bien["tipo"], bien.get("descripcion", "").lower()
    if tipo == "Inmueble":
        return "inmueble"
    if tipo == "Sin garantía":
        return "sin_garantia"
    if tipo == "Bienes muebles":
        return "muebles"
    if tipo == "Maquinaria" or PATRON_PESADO.search(descripcion):
        return "pesado"
    if re.search(r"\bmoto", descripcion):
        return "moto"
    return "liviano"


def costas_personales(monto_deuda: int) -> int:
    costas = round(monto_deuda * PORCENTAJE_COSTAS / 1000) * 1000
    return min(max(costas, COSTAS_MINIMAS_CLP), COSTAS_MAXIMAS_CLP)


def estimar_riesgo(caso: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
    """Devuelve el riesgo total en CLP y su desglose. Sin apremio en curso el riesgo es 0."""
    if caso["estado_judicial"] not in ESTADOS_JUDICIALES_APREMIO:
        return 0, []

    bien = caso["bien_garantia"]
    clase = clase_bien(bien)
    partidas = [("Receptor judicial", HONORARIO_RECEPTOR_CLP)]
    if caso["estado_judicial"] in APREMIOS_CON_RETIRO and clase in TARIFAS_RETIRO:
        tarifa = TARIFAS_RETIRO[clase]
        partidas += [
            (tarifa.medio, tarifa.retiro),
            (f"Custodia {DIAS_CUSTODIA} días", tarifa.custodia_diaria * DIAS_CUSTODIA),
            ("Devolución del bien", tarifa.devolucion),
        ]
    elif bien["tipo"] in INSCRIPCION_ALZAMIENTO:
        partidas.append(INSCRIPCION_ALZAMIENTO[bien["tipo"]])
    partidas.append((f"Costas personales ({PORCENTAJE_COSTAS:.0%} de la deuda)", costas_personales(int(caso["monto_deuda"]))))

    detalle = [{"concepto": concepto, "monto": monto} for concepto, monto in partidas]
    return sum(monto for _, monto in partidas), detalle
