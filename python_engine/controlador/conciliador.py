"""
Conciliación de planillas estructuradas de mandantes.

Las planillas que envían bancos y financieras cada cierto tiempo son una fuente
de entrada más del repositorio: cada registro se cruza contra los avisos de pago
pendientes y actualiza su estado. El detector reacciona después a esos cambios
(por ejemplo, un pago confirmado con la causa activa dispara EC-03).
"""

from datetime import datetime
from typing import Any, Dict, List

from modelo.entidades import AvisoPago, a_iso
from modelo.repositorio import Repositorio


def normalizar_rut(rut: Any) -> str:
    return str(rut or "").replace(".", "").replace("-", "").strip().upper()


def conciliar_planilla(
    repo: Repositorio,
    registros: List[Dict[str, Any]],
    usuario: str,
    ahora: datetime,
) -> Dict[str, Any]:
    resultado = {"confirmados": [], "observados": [], "nuevos": [], "sin_caso": []}

    for reg in registros:
        rut = normalizar_rut(reg.get("rut"))
        monto = int(reg.get("monto", 0))
        operacion = str(reg.get("codigo_operacion", "")).strip().upper()
        mandante = reg.get("mandante", "Mandante")

        aviso = next(
            (
                a for a in repo.listar("avisos")
                if a["estado"] in ("informado", "observado")
                and (
                    (operacion and str(a["datos_extraidos"].get("numero_operacion", "")).strip().upper() == operacion)
                    or (rut and normalizar_rut(a["datos_extraidos"].get("rut_depositante")) == rut and a["monto"] == monto)
                )
            ),
            None,
        )

        if aviso:
            if aviso["monto"] == monto:
                cambios = {"estado": "confirmado", "observaciones": f"Conciliado con planilla {mandante} (operación {operacion})."}
                destino = "confirmados"
            else:
                cambios = {
                    "estado": "observado",
                    "observaciones": f"Diferencia: informado ${aviso['monto']:,.0f} vs planilla ${monto:,.0f}.".replace(",", "."),
                }
                destino = "observados"
            repo.actualizar("avisos", aviso["id"], cambios, usuario, "Integración",
                            f"Conciliación planilla {mandante}", ahora)
            resultado[destino].append(aviso["id"])
            continue

        caso = next((c for c in repo.listar("casos") if normalizar_rut(c["deudor"]["rut"]) == rut), None)
        if not caso:
            resultado["sin_caso"].append({"rut": reg.get("rut"), "monto": monto, "codigo_operacion": operacion})
            continue

        # Pago que llegó por la planilla sin aviso previo del deudor.
        nuevo = repo.insertar("avisos", AvisoPago(
            id=repo.siguiente_id("avisos"),
            caso_id=caso["id"],
            fecha_recepcion=a_iso(ahora),
            monto=monto,
            origen="Planilla mandante",
            canal="Planilla Mandante",
            estado="confirmado",
            datos_extraidos={"numero_operacion": operacion, "rut_depositante": reg.get("rut"), "fecha_hora_operacion": reg.get("fecha_pago")},
            observaciones=f"Pago informado directamente por {mandante}, sin aviso previo del deudor.",
        ))
        repo.registrar_historial(
            usuario=usuario, area="Integración", accion="Pago registrado desde planilla de mandante",
            detalle=f"Aviso {nuevo['id']} por ${monto:,.0f} confirmado por {mandante}.".replace(",", "."),
            entidad="Aviso", entidad_id=nuevo["id"], caso_id=caso["id"], ahora=ahora,
        )
        resultado["nuevos"].append(nuevo["id"])

    return resultado
