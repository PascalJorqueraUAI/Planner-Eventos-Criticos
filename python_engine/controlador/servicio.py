"""
Fachada de casos de uso que expone la API REST.

Cada operación que modifica el repositorio termina con un ciclo de detección:
el detector compara el nuevo estado contra el catálogo y el asignador reparte
las tareas que resulten. Así una actualización del CRM, un comprobante o una
planilla de mandante generan sus alertas en el mismo instante.
"""

from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from controlador import conciliador, detector, extraccion, seguimiento
from controlador.asignador import MATRIZ_RACI, PESOS, asignar_lote, carga_actual, perfil_historico
from controlador.catalogo_eventos import catalogo_serializado
from controlador.conciliador import normalizar_rut
from controlador.extraccion import ConfigExtraccion
from controlador.trazabilidad import calcular_metricas
from modelo.datos_iniciales import crear_datos_iniciales
from modelo.entidades import (
    ESTADOS_COMERCIALES,
    ESTADOS_JUDICIALES,
    AvisoPago,
    a_iso,
)
from modelo.repositorio import Repositorio

CAMPOS_CASO_EDITABLES = ("estado_comercial", "estado_judicial", "fecha_diligencia", "responsable_comercial", "responsable_judicial")


class Servicio:
    def __init__(self, repo: Repositorio, reloj=datetime.now, config_extraccion: Optional[ConfigExtraccion] = None,
                 inicializar: bool = True):
        self.repo = repo
        self.reloj = reloj
        self.config_extraccion = config_extraccion or ConfigExtraccion.desde_entorno()
        if inicializar and repo.vacio:
            self.reiniciar()

    def ahora(self) -> datetime:
        return self.reloj().replace(microsecond=0)

    # --- Ciclo de detección ---------------------------------------------------------

    def ciclo_deteccion(self, usuario: str = "Detector de eventos") -> Dict[str, Any]:
        """
        1. Calendario de ausencias → disponibilidad (y reasignación de lo pendiente).
        2. Tareas vencidas → reasignación o escalamiento a jefatura.
        3. Detector → eventos nuevos, que el asignador reparte en un solo lote.
        """
        ahora = self.ahora()
        ausencias = seguimiento.sincronizar_ausencias(self.repo, ahora)
        escaladas = seguimiento.escalar_vencidas(self.repo, ahora)
        nuevos = detector.escanear(self.repo, ahora, usuario)
        tareas = [t for e in nuevos for t in e["tareas"]]
        asignar_lote(self.repo, tareas, ahora)
        return {
            "eventos_nuevos": [{k: v for k, v in e.items() if k != "tareas"} for e in nuevos],
            "tareas_nuevas": len(tareas),
            "tareas_escaladas": [{"id": t["id"], "nivel": t["nivel_escalamiento"]} for t in escaladas],
            "disponibilidad_actualizada": ausencias,
            "escaneado_en": a_iso(ahora),
        }

    def escanear(self) -> Dict[str, Any]:
        return self._cerrar_operacion({})

    def _cerrar_operacion(self, resultado: Dict[str, Any]) -> Dict[str, Any]:
        resultado["deteccion"] = self.ciclo_deteccion()
        self.repo.guardar()
        return resultado

    # --- Lectura ------------------------------------------------------------------

    def estado(self) -> Dict[str, Any]:
        """Todo lo que la Vista necesita, con los campos derivados ya calculados."""
        ahora = self.ahora()
        tareas = [{**t, "vencida": seguimiento.esta_vencida(t, ahora)} for t in self.repo.listar("tareas")]
        colaboradores = [
            {
                **c,
                "carga_actual": carga_actual(self.repo, c),
                "historico": perfil_historico(self.repo, c["id"]),
                "historico_por_tipo": {tipo: perfil_historico(self.repo, c["id"], tipo) for tipo in c["competencias"]},
            }
            for c in self.repo.listar("colaboradores")
        ]
        return {
            "ahora": a_iso(ahora),
            "casos": self.repo.listar("casos"),
            "avisos": self.repo.listar("avisos"),
            "eventos": self.repo.listar("eventos"),
            "tareas": tareas,
            "colaboradores": colaboradores,
            "historial": list(reversed(self.repo.listar("historial")))[:300],
            "catalogo": catalogo_serializado(),
            "matriz_raci": MATRIZ_RACI,
            "pesos_asignacion": PESOS,
            "estados": {"comercial": ESTADOS_COMERCIALES, "judicial": ESTADOS_JUDICIALES},
            "metricas": calcular_metricas(self.repo, ahora),
            "ultimo_escaneo": self.repo.datos["meta"].get("ultimo_escaneo"),
            "extraccion": self.config_extraccion.publica(),
            "tratamientos": list(reversed(self.repo.listar("tratamientos")))[:100],
        }

    def obtener_caso(self, caso_id: str) -> Dict[str, Any]:
        return {
            "caso": self.repo.obtener("casos", caso_id),
            "avisos": self.repo.filtrar("avisos", caso_id=caso_id),
            "eventos": self.repo.filtrar("eventos", caso_id=caso_id),
            "tareas": self.repo.filtrar("tareas", caso_id=caso_id),
            "historial": [h for h in reversed(self.repo.listar("historial")) if h.get("caso_id") == caso_id],
        }

    # --- Integración: entradas al repositorio -----------------------------------------

    def actualizar_caso(self, caso_id: str, cambios: Dict[str, Any], usuario: str) -> Dict[str, Any]:
        """Actualización de un caso enviada por el CRM de Cobgestion (o editada a mano)."""
        invalidos = set(cambios) - set(CAMPOS_CASO_EDITABLES)
        if invalidos:
            raise ValueError(f"Campos no editables: {', '.join(sorted(invalidos))}")
        if "estado_judicial" in cambios and cambios["estado_judicial"] not in ESTADOS_JUDICIALES:
            raise ValueError(f"Estado judicial desconocido: {cambios['estado_judicial']}")
        if "estado_comercial" in cambios and cambios["estado_comercial"] not in ESTADOS_COMERCIALES:
            raise ValueError(f"Estado comercial desconocido: {cambios['estado_comercial']}")
        caso = self.repo.actualizar("casos", caso_id, cambios, usuario, "Integración",
                                    "Actualización de caso desde CRM", self.ahora())
        return self._cerrar_operacion({"caso": caso})

    def ingresar_aviso(self, datos: Dict[str, Any], usuario: str) -> Dict[str, Any]:
        """Comprobante no estructurado (pantallazo, correo, aviso bancario) ya extraído."""
        ahora = self.ahora()
        extraidos = datos.get("datos_extraidos") or {}
        caso_id = datos.get("caso_id") or self._caso_por_rut(extraidos.get("rut_depositante"))
        if not caso_id:
            raise ValueError("No se pudo asociar el comprobante a un caso (indique caso_id o un RUT conocido)")
        self.repo.obtener("casos", caso_id)
        aviso = self.repo.insertar("avisos", AvisoPago(
            id=self.repo.siguiente_id("avisos"),
            caso_id=caso_id,
            fecha_recepcion=datos.get("fecha_recepcion") or a_iso(ahora),
            monto=int(datos.get("monto") or 0),
            origen=datos.get("origen", "Correo cliente"),
            canal=datos.get("canal", "Email"),
            datos_extraidos=extraidos,
            observaciones=datos.get("observaciones", ""),
        ))
        self.repo.registrar_historial(
            usuario=usuario, area="Integración", accion="Comprobante de pago recibido",
            detalle=f"Aviso {aviso['id']} por ${aviso['monto']:,.0f} vía {aviso['canal']}.".replace(",", "."),
            entidad="Aviso", entidad_id=aviso["id"], caso_id=caso_id, ahora=ahora,
        )
        return self._cerrar_operacion({"aviso": aviso})

    def conciliar_planilla(self, registros: List[Dict[str, Any]], usuario: str) -> Dict[str, Any]:
        resultado = conciliador.conciliar_planilla(self.repo, registros, usuario, self.ahora())
        return self._cerrar_operacion({"conciliacion": resultado})

    def extraer_comprobante(self, datos: Dict[str, Any], usuario: str) -> Dict[str, Any]:
        """
        Solo lectura del repositorio: prellena el formulario de registro. Si hubo envío a
        un tercero, devuelve el registro de tratamiento para que se guarde aparte.
        """
        nombres = [c["deudor"]["nombre"] for c in self.repo.listar("casos")]
        resultado, registro = extraccion.extraer_comprobante(
            texto=datos.get("texto", ""),
            imagen_base64=datos.get("imagen_base64"),
            mime_type=datos.get("mime_type"),
            confirmacion_operador=bool(datos.get("confirmacion_operador")),
            usuario=usuario,
            nombres_conocidos=nombres,
            config=self.config_extraccion,
            ahora=self.ahora(),
        )
        return {"datos": resultado, "tratamiento": asdict(registro) if registro else None}

    def registrar_tratamiento(self, tratamiento: Dict[str, Any]) -> Dict[str, Any]:
        registro = self.repo.insertar("tratamientos", {**tratamiento, "id": self.repo.siguiente_id("tratamientos")})
        self.repo.registrar_historial(
            usuario=registro["usuario"], area="Protección de datos",
            accion=f"Datos enviados a encargado del tratamiento ({registro['resultado']})",
            detalle=f"{registro['tipo_entrada']} → {registro['proveedor']}. Medidas: {', '.join(registro['medidas'])}.",
            entidad="Tratamiento", entidad_id=registro["id"], ahora=self.ahora(),
        )
        self.repo.guardar()
        return registro

    def _caso_por_rut(self, rut: Optional[str]) -> Optional[str]:
        objetivo = normalizar_rut(rut)
        if not objetivo:
            return None
        caso = next((c for c in self.repo.listar("casos") if normalizar_rut(c["deudor"]["rut"]) == objetivo), None)
        return caso["id"] if caso else None

    # --- Asignación y seguimiento ---------------------------------------------------

    def atender_tarea(self, tarea_id: str, resultado: str, notas: str, usuario: str) -> Dict[str, Any]:
        return self._cerrar_operacion(seguimiento.atender_tarea(self.repo, tarea_id, resultado, notas, usuario, self.ahora()))

    def reasignar_tarea(self, tarea_id: str, motivo: str, usuario: str) -> Dict[str, Any]:
        tarea = seguimiento.reasignar_tarea(self.repo, tarea_id, motivo, usuario, self.ahora())
        return self._cerrar_operacion({"tarea": tarea})

    def cambiar_disponibilidad(self, colaborador_id: str, disponible: bool, motivo: str, usuario: str) -> Dict[str, Any]:
        reasignadas = seguimiento.cambiar_disponibilidad(self.repo, colaborador_id, disponible, motivo, usuario, self.ahora())
        return self._cerrar_operacion({"reasignadas": [t["id"] for t in reasignadas]})

    def registrar_ausencia(self, colaborador_id: str, desde: str, hasta: str, motivo: str, usuario: str) -> Dict[str, Any]:
        """Ausencia informada por RR.HH. o el CRM; también se puede cargar desde la interfaz."""
        reasignadas = seguimiento.registrar_ausencia(self.repo, colaborador_id, desde, hasta, motivo, usuario, self.ahora())
        return self._cerrar_operacion({"reasignadas": [t["id"] for t in reasignadas]})

    # --- Administración -------------------------------------------------------------

    def reiniciar(self) -> Dict[str, Any]:
        ahora = self.ahora()
        self.repo.reemplazar(crear_datos_iniciales(ahora))
        self.repo.registrar_historial(
            usuario="Integración sandbox", area="Integración", accion="Carga inicial del repositorio",
            detalle="Casos, avisos, colaboradores e historial de desempeño cargados desde el entorno de pruebas.",
            entidad="Caso", entidad_id="*", ahora=ahora,
        )
        return self._cerrar_operacion({"mensaje": "Repositorio reiniciado con los datos del sandbox"})

    def exportar(self, directorio: str) -> Dict[str, Any]:
        return {"archivos": self.repo.exportar_csv(directorio)}
