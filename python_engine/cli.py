"""
CLI y Punto de Entrada del Motor Python para Cobgestion
Permite la ejecución desde terminal o invocación como servicio backend por Express.
Comandos:
  status                Muestra resumen de casos, eventos críticos y ahorro financiero
  ingest-notice <json>  Ingresa aviso no estructurado y dispara eventos críticos
  resolve-judicial      Registra resolución y suspensión judicial
  resolve-commercial    Registra verificación comercial
  reconcile-batch       Concilia planilla estructurada de mandante
  export-excel          Exporta las 6 hojas a CSV/Excel
  run-tests             Ejecuta los tests unitarios
"""

import sys
import json
import argparse
import os
from repositorio_cobgestion import RepositorioCobgestion
from conciliador_mandantes import ConciliadorMandantes

def main():
    parser = argparse.ArgumentParser(description="Motor Python Cobgestion - Detección de Eventos Críticos")
    parser.add_argument("command", choices=[
        "status",
        "ingest-notice",
        "resolve-judicial",
        "resolve-commercial",
        "reconcile-batch",
        "export-excel",
        "reset-data"
    ])
    parser.add_argument("--json-input", help="Payload en JSON para comandos de entrada", default=None)
    parser.add_argument("--evento-id", help="ID del evento", default=None)
    parser.add_argument("--accion", help="Acción judicial", default=None)
    parser.add_argument("--escrito", action="store_true", help="Escrito presentado en tribunal")
    parser.add_argument("--estado-pago", help="Estado pago comercial (confirmado / observado)", default=None)
    parser.add_argument("--usuario", help="Nombre del usuario", default="Usuario Sistema")
    parser.add_argument("--notas", help="Notas u observaciones", default="")

    args = parser.parse_args()
    repo = RepositorioCobgestion()

    if args.command == "status":
        eventos = repo.data["eventos"]
        casos = repo.data["casos"]
        tareas = repo.data["tareas"]
        avisos = repo.data["avisos"]

        activos = [e for e in eventos if not e.get("cerrado")]
        alertas_jud = [e for e in eventos if not e.get("cerrado") and not e.get("resolucion_judicial")]
        
        # Ahorro: 600.000 CLP por cada evento crítico donde se suspendió la incautación oportunamente
        suspensiones = sum(
            1 for e in eventos
            if e.get("resolucion_judicial", {}).get("accion_ejecutada") in [
                "Suspender tramitación de incautación",
                "Notificar receptor judicial",
                "Levantar encargo judicial"
            ]
        )
        ahorro = suspensiones * 600000

        resumen = {
            "total_casos": len(casos),
            "total_avisos": len(avisos),
            "eventos_criticos_activos": len(activos),
            "alertas_judiciales_pendientes": len(alertas_jud),
            "ahorro_perdidas_prevenido_clp": ahorro,
            "tareas_pendientes": len([t for t in tareas if t.get("estado") == "Pendiente"]),
            "casos_alto_riesgo_vehicular": len([c for c in casos if c.get("bien_en_garantia", {}).get("tipo") == "Vehículo" and "incautación" in c.get("estado_judicial", "").lower()])
        }
        print(json.dumps(resumen, ensure_ascii=False, indent=2))

    elif args.command == "ingest-notice":
        if not args.json_input:
            print(json.dumps({"error": "Se requiere --json-input con los datos del aviso"}))
            sys.exit(1)
        data = json.loads(args.json_input)
        resultado = repo.registrar_aviso_y_detectar(data, usuario=args.usuario)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))

    elif args.command == "resolve-judicial":
        if not args.evento_id or not args.accion:
            print(json.dumps({"error": "Se requiere --evento-id y --accion"}))
            sys.exit(1)
        resultado = repo.resolver_tarea_judicial(
            evento_id=args.evento_id,
            accion=args.accion,
            escrito=args.escrito,
            usuario=args.usuario,
            notas=args.notas
        )
        print(json.dumps(resultado, ensure_ascii=False, indent=2))

    elif args.command == "resolve-commercial":
        if not args.evento_id or not args.estado_pago:
            print(json.dumps({"error": "Se requiere --evento-id y --estado-pago"}))
            sys.exit(1)
        resultado = repo.resolver_tarea_comercial(
            evento_id=args.evento_id,
            nuevo_estado_pago=args.estado_pago,
            usuario=args.usuario,
            notas=args.notas
        )
        print(json.dumps(resultado, ensure_ascii=False, indent=2))

    elif args.command == "reconcile-batch":
        if not args.json_input:
            print(json.dumps({"error": "Se requiere --json-input con la lista de pagos de mandante"}))
            sys.exit(1)
        lote = json.loads(args.json_input)
        avisos_raw = repo.data["avisos"]
        # Convertir a objetos temporales
        from models import AvisoPago, DatosExtraidos
        avisos_objs = []
        for a in avisos_raw:
            datos_ext = DatosExtraidos(**a.get("datos_extraidos", {}))
            avisos_objs.append(AvisoPago(
                id=a["id"],
                caso_id=a["caso_id"],
                fecha_recepcion=a["fecha_recepcion"],
                monto_informado=a["monto_informado"],
                origen=a["origen"],
                canal=a["canal"],
                estado_verificacion=a["estado_verificacion"],
                datos_extraidos=datos_ext
            ))

        resultado = ConciliadorMandantes.conciliar_lote(avisos_objs, lote, usuario=args.usuario)
        # Sincronizar cambios en repo
        for av_act in resultado["avisos_actualizados"]:
            target = next((x for x in repo.data["avisos"] if x["id"] == av_act.id), None)
            if target:
                target["estado_verificacion"] = av_act.estado_verificacion
                target["observaciones_comerciales"] = av_act.observaciones_comerciales

        from dataclasses import asdict
        for pc in resultado["pagos_conciliados"]:
            repo.data["pagos_conciliados"].insert(0, asdict(pc))

        repo.guardar_datos()
        
        # Responder JSON
        resp = {
            "conciliados_exitosos": resultado["conciliados_exitosos"],
            "discrepancias_encontradas": resultado["discrepancias_encontradas"],
            "detalle_discrepancias": resultado["detalle_discrepancias"]
        }
        print(json.dumps(resp, ensure_ascii=False, indent=2))

    elif args.command == "export-excel":
        archivos = repo.exportar_csv("./exports")
        print(json.dumps({"mensaje": "Archivos CSV (Excel) exportados", "archivos": archivos}, ensure_ascii=False, indent=2))

    elif args.command == "reset-data":
        from repositorio_cobgestion import _init_default_data
        data = _init_default_data()
        repo.guardar_datos(data)
        print(json.dumps({"mensaje": "Datos restablecidos con éxito"}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
