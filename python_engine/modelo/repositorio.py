"""
Repositorio centralizado (capa Modelo).

Una sola "planilla" con todas las hojas del sistema: casos, avisos de pago,
eventos críticos, tareas, colaboradores, historial de desempeño e historial de
cambios. Toda modificación pasa por `actualizar`, que deja registrado en el
historial qué campo cambió, su valor anterior, el nuevo, quién y cuándo.
"""

import csv
import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from modelo.entidades import RegistroHistorial, a_iso

RUTA_DATOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_store.json")

COLECCIONES = (
    "casos",
    "avisos",
    "eventos",
    "tareas",
    "colaboradores",
    "historial_desempeno",
    "historial",
    "tratamientos",
)

# Prefijo de id usado por cada colección.
PREFIJOS = {
    "casos": "CASO",
    "avisos": "AVP",
    "eventos": "EVT",
    "tareas": "TSK",
    "colaboradores": "COL",
    "historial": "LOG",
    "tratamientos": "TRT",
}


class Repositorio:
    def __init__(self, ruta: Optional[str] = RUTA_DATOS, datos: Optional[Dict[str, Any]] = None):
        """`ruta=None` crea un repositorio en memoria (usado por las pruebas)."""
        self.ruta = ruta
        if datos is not None:
            self.datos = datos
        elif ruta and os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as f:
                self.datos = json.load(f)
        else:
            self.datos = {}
        for coleccion in COLECCIONES:
            self.datos.setdefault(coleccion, [])
        self.datos.setdefault("meta", {"contadores": {}, "ultimo_escaneo": None})

    @property
    def vacio(self) -> bool:
        return not self.datos["casos"]

    def reemplazar(self, datos: Dict[str, Any]) -> None:
        self.__init__(self.ruta, datos)

    def guardar(self) -> None:
        if not self.ruta:
            return
        temporal = self.ruta + ".tmp"
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(self.datos, f, ensure_ascii=False, indent=2)
        os.replace(temporal, self.ruta)

    # --- Lectura ----------------------------------------------------------------

    def listar(self, coleccion: str) -> List[Dict[str, Any]]:
        return self.datos[coleccion]

    def buscar(self, coleccion: str, id_: str) -> Optional[Dict[str, Any]]:
        return next((r for r in self.datos[coleccion] if r.get("id") == id_), None)

    def obtener(self, coleccion: str, id_: str) -> Dict[str, Any]:
        registro = self.buscar(coleccion, id_)
        if registro is None:
            raise ValueError(f"No existe {coleccion[:-1]} con id {id_}")
        return registro

    def filtrar(self, coleccion: str, **criterios: Any) -> List[Dict[str, Any]]:
        return [
            r for r in self.datos[coleccion]
            if all(r.get(campo) == valor for campo, valor in criterios.items())
        ]

    # --- Escritura --------------------------------------------------------------

    def siguiente_id(self, coleccion: str) -> str:
        contadores = self.datos["meta"]["contadores"]
        contadores[coleccion] = contadores.get(coleccion, 0) + 1
        return f"{PREFIJOS[coleccion]}-{contadores[coleccion]:04d}"

    def insertar(self, coleccion: str, entidad: Any) -> Dict[str, Any]:
        registro = asdict(entidad) if is_dataclass(entidad) else dict(entidad)
        self.datos[coleccion].append(registro)
        return registro

    def actualizar(
        self,
        coleccion: str,
        id_: str,
        cambios: Dict[str, Any],
        usuario: str,
        area: str,
        accion: str,
        ahora: datetime,
        detalle: str = "",
    ) -> Dict[str, Any]:
        """Aplica cambios a un registro y deja la diferencia en el historial."""
        registro = self.obtener(coleccion, id_)
        diferencias = {
            campo: [registro.get(campo), valor]
            for campo, valor in cambios.items()
            if registro.get(campo) != valor
        }
        if not diferencias:
            return registro
        registro.update(cambios)
        if coleccion == "casos":
            registro["ultima_actualizacion"] = a_iso(ahora)
        caso_id = registro["id"] if coleccion == "casos" else registro.get("caso_id")
        self.registrar_historial(
            usuario=usuario,
            area=area,
            accion=accion,
            detalle=detalle or ", ".join(f"{c}: {a} → {d}" for c, (a, d) in diferencias.items()),
            entidad=ENTIDAD_POR_COLECCION[coleccion],
            entidad_id=id_,
            caso_id=caso_id,
            ahora=ahora,
            cambios=diferencias,
        )
        return registro

    def registrar_historial(
        self,
        usuario: str,
        area: str,
        accion: str,
        detalle: str,
        entidad: str,
        entidad_id: str,
        ahora: datetime,
        caso_id: Optional[str] = None,
        cambios: Optional[Dict[str, List[Any]]] = None,
    ) -> Dict[str, Any]:
        return self.insertar("historial", RegistroHistorial(
            id=self.siguiente_id("historial"),
            timestamp=a_iso(ahora),
            usuario=usuario,
            area=area,
            accion=accion,
            detalle=detalle,
            entidad=entidad,
            entidad_id=entidad_id,
            caso_id=caso_id,
            cambios=cambios or {},
        ))

    # --- Exportación ------------------------------------------------------------

    def exportar_csv(self, directorio: str) -> List[str]:
        """Exporta cada hoja del repositorio a un CSV compatible con Excel."""
        os.makedirs(directorio, exist_ok=True)
        archivos = []
        for coleccion in COLECCIONES:
            registros = self.datos[coleccion]
            ruta = os.path.join(directorio, f"Cobgestion_{coleccion}.csv")
            columnas = list(registros[0].keys()) if registros else []
            with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(columnas)
                for r in registros:
                    writer.writerow([_celda(r.get(c)) for c in columnas])
            archivos.append(ruta)
        return archivos


ENTIDAD_POR_COLECCION = {
    "casos": "Caso",
    "avisos": "Aviso",
    "eventos": "Evento",
    "tareas": "Tarea",
    "colaboradores": "Colaborador",
}


def _celda(valor: Any) -> Any:
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False)
    return "" if valor is None else valor
