import os
import unittest
from unittest import mock

import cli
from controlador import permisos
from controlador.permisos import PermisoDenegado, actor_desde, autorizar, vista_para
from modelo.usuarios import asegurar_usuarios, hash_clave
from tests.utilidades import Reloj, servicio_de_prueba, tareas_del_caso


def usuario_de(servicio, colaborador_id=None, cargo=None):
    return next(u for u in servicio.repo.listar("usuarios")
                if (colaborador_id and u.get("colaborador_id") == colaborador_id) or (cargo and u["cargo"] == cargo))


class TestLogin(unittest.TestCase):
    def setUp(self):
        self.servicio = servicio_de_prueba()

    def test_gerencia_general_y_colaboradores_tienen_cuenta(self):
        usuarios = self.servicio.repo.listar("usuarios")
        gerente = next(u for u in usuarios if u["cargo"] == "Gerente General")
        self.assertEqual(gerente["nombre"], "Fernando García-Huidobro")
        self.assertEqual(gerente["email"], "fernando.garcia-huidobro@cobgestion.cl")
        self.assertEqual({u["nivel"] for u in usuarios if u["cargo"] in ("Gerente General", "Subgerente")}, {1})
        self.assertEqual({u["nivel"] for u in usuarios if u["cargo"].startswith("Gerente ") and u["area"] != "Gerencia"}, {2})
        self.assertEqual(len({u["email"] for u in usuarios}), len(usuarios))

    def test_clave_de_demostracion(self):
        usuario = self.servicio.iniciar_sesion("PATRICIA.LAGOS@cobgestion.cl", "cobgestion")
        self.assertEqual(usuario["nivel"], 2)
        self.assertNotIn("clave_hash", usuario)
        with self.assertRaises(ValueError):
            self.servicio.iniciar_sesion("patricia.lagos@cobgestion.cl", "otra")

    def test_sin_modo_demo_la_clave_de_demostracion_no_sirve(self):
        with mock.patch.dict(os.environ, {"MODO_DEMO": "no"}):
            with self.assertRaises(ValueError):
                self.servicio.iniciar_sesion("patricia.lagos@cobgestion.cl", "cobgestion")
            self.assertEqual(self.servicio.usuarios_demo(), {"modo_demo": False})

    def test_clave_propia_con_hash(self):
        usuario = usuario_de(self.servicio, cargo="Gerente General")
        usuario["clave_hash"] = hash_clave("Segura-2026")
        self.assertEqual(self.servicio.iniciar_sesion(usuario["email"], "Segura-2026")["id"], usuario["id"])
        with self.assertRaises(ValueError):
            self.servicio.iniciar_sesion(usuario["email"], "cobgestion")

    def test_repositorio_anterior_al_login_se_migra(self):
        datos = self.servicio.repo.datos
        datos["usuarios"] = []
        jefa = next(c for c in datos["colaboradores"] if c["cargo"] == "Gerente Comercial")
        jefa["cargo"] = "Jefe Comercial"
        self.assertTrue(asegurar_usuarios(datos))
        self.assertEqual(jefa["cargo"], "Gerente Comercial")
        self.assertEqual(len(datos["usuarios"]), len(datos["colaboradores"]) + 2)

    def test_sesion_invalida(self):
        with self.assertRaises(PermisoDenegado):
            actor_desde(self.servicio.repo, "USR-9999")


class TestPermisos(unittest.TestCase):
    def setUp(self):
        self.servicio = servicio_de_prueba()
        self.repo = self.servicio.repo
        _, self.tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        comercial = self.tareas["Comercial"]
        self.ejecutivo = actor_desde(self.repo, usuario_de(self.servicio, comercial["responsable_id"])["id"])
        self.gerente_comercial = actor_desde(self.repo, usuario_de(self.servicio, cargo="Gerente Comercial")["id"])
        self.gerente_judicial = actor_desde(self.repo, usuario_de(self.servicio, cargo="Gerente Judicial")["id"])
        self.gerente_general = actor_desde(self.repo, usuario_de(self.servicio, cargo="Gerente General")["id"])

    def permitido(self, actor, comando, **datos):
        try:
            autorizar(self.repo, actor, comando, datos)
            return True
        except PermisoDenegado:
            return False

    def test_cada_quien_atiende_lo_suyo(self):
        comercial, judicial = self.tareas["Comercial"]["id"], self.tareas["Judicial"]["id"]
        self.assertTrue(self.permitido(self.ejecutivo, "atender-tarea", tarea_id=comercial))
        self.assertFalse(self.permitido(self.ejecutivo, "atender-tarea", tarea_id=judicial))
        self.assertTrue(self.permitido(self.gerente_comercial, "atender-tarea", tarea_id=comercial))
        self.assertFalse(self.permitido(self.gerente_comercial, "atender-tarea", tarea_id=judicial))
        self.assertTrue(self.permitido(self.gerente_general, "atender-tarea", tarea_id=judicial))

    def test_reasignar_es_de_la_gerencia_del_area(self):
        comercial = self.tareas["Comercial"]["id"]
        self.assertFalse(self.permitido(self.ejecutivo, "reasignar-tarea", tarea_id=comercial))
        self.assertTrue(self.permitido(self.gerente_comercial, "reasignar-tarea", tarea_id=comercial))
        self.assertFalse(self.permitido(self.gerente_judicial, "reasignar-tarea", tarea_id=comercial))

    def test_crear_exportar_y_reiniciar(self):
        self.assertFalse(self.permitido(self.ejecutivo, "crear-caso"))
        self.assertTrue(self.permitido(self.gerente_judicial, "crear-caso"))
        self.assertFalse(self.permitido(self.gerente_comercial, "exportar"))
        self.assertTrue(self.permitido(self.gerente_general, "exportar"))
        self.assertFalse(self.permitido(self.gerente_comercial, "reiniciar"))

    def test_campos_del_caso_segun_area(self):
        caso_propio = "CASO-1052"
        self.assertTrue(self.permitido(self.ejecutivo, "actualizar-caso", caso_id=caso_propio,
                                       cambios={"estado_comercial": "Pagado"}))
        self.assertFalse(self.permitido(self.ejecutivo, "actualizar-caso", caso_id=caso_propio,
                                        cambios={"estado_judicial": "Terminado por pago"}))
        self.assertFalse(self.permitido(self.ejecutivo, "actualizar-caso", caso_id=caso_propio,
                                        cambios={"responsable_comercial": "COL-0003"}))
        self.assertTrue(self.permitido(self.gerente_comercial, "actualizar-caso", caso_id=caso_propio,
                                       cambios={"responsable_comercial": "COL-0003"}))
        ajeno = next(c["id"] for c in self.repo.listar("casos") if c["id"] not in permisos.casos_propios(self.repo, self.ejecutivo))
        self.assertFalse(self.permitido(self.ejecutivo, "actualizar-caso", caso_id=ajeno, cambios={"estado_comercial": "Pagado"}))

    def test_ausencias_propias(self):
        propio = self.ejecutivo.colaborador_id
        otro = next(c["id"] for c in self.repo.listar("colaboradores") if c["id"] != propio and c["area"] == "Comercial")
        self.assertTrue(self.permitido(self.ejecutivo, "registrar-ausencia", colaborador_id=propio))
        self.assertFalse(self.permitido(self.ejecutivo, "registrar-ausencia", colaborador_id=otro))
        self.assertFalse(self.permitido(self.ejecutivo, "disponibilidad", colaborador_id=propio))
        self.assertTrue(self.permitido(self.gerente_comercial, "disponibilidad", colaborador_id=otro))

    def test_la_integracion_no_atiende_tareas(self):
        self.assertTrue(self.permitido(permisos.INTEGRACION, "ingresar-aviso"))
        self.assertFalse(self.permitido(permisos.INTEGRACION, "atender-tarea", tarea_id=self.tareas["Comercial"]["id"]))

    def test_la_cli_rechaza_y_firma_con_el_usuario_de_la_sesion(self):
        with self.assertRaises(PermisoDenegado):
            cli.ejecutar(self.servicio, "exportar", {"actor": self.ejecutivo.id})
        tarea = self.tareas["Comercial"]
        cli.ejecutar(self.servicio, "atender-tarea", {
            "actor": self.ejecutivo.id, "tarea_id": tarea["id"], "resultado": "Pago confirmado", "usuario": "Otro nombre",
        })
        self.assertEqual(self.repo.obtener("tareas", tarea["id"])["atendida_por"], self.ejecutivo.nombre)


class TestVistaSegunNivel(unittest.TestCase):
    def setUp(self):
        self.servicio = servicio_de_prueba()
        self.repo = self.servicio.repo
        self.estado = self.servicio.estado()

    def vista(self, **kw):
        return vista_para(self.repo, actor_desde(self.repo, usuario_de(self.servicio, **kw)["id"]), self.estado)

    def test_nivel_3_ve_todos_los_casos_pero_sin_datos_personales_ajenos(self):
        actor = actor_desde(self.repo, usuario_de(self.servicio, colaborador_id="COL-0003")["id"])
        propios = permisos.casos_propios(self.repo, actor)
        vista = vista_para(self.repo, actor, self.estado)
        self.assertEqual(len(vista["casos"]), len(self.estado["casos"]))
        ajeno = next(c for c in vista["casos"] if c["id"] == "CASO-1052")
        self.assertNotIn("CASO-1052", propios)
        self.assertEqual(ajeno["deudor"]["nombre"], "C. S. M.")
        self.assertEqual(ajeno["deudor"]["rut"], "(oculto)")
        self.assertEqual(ajeno["bien_garantia"]["patente"], "(oculto)")
        self.assertTrue(ajeno["restringido"])
        texto = repr([t for t in vista["tareas"] if t["caso_id"] == "CASO-1052"]) + repr(vista["avisos"]) + repr(vista["historial"])
        for dato in ("Carlos Silva Mendoza", "16.482.910-K", "BB-CL-44"):
            self.assertNotIn(dato, texto)

    def test_empresas_mantienen_su_nombre(self):
        vista = self.vista(colaborador_id="COL-0003")
        empresa = next(c for c in vista["casos"] if c["deudor"]["nombre"].endswith("SpA"))
        self.assertNotEqual(empresa["deudor"]["rut"], "(oculto)")

    def test_motivo_de_ausencia_ajena_es_reservado(self):
        vista = self.vista(colaborador_id="COL-0003")
        camila = next(c for c in vista["colaboradores"] if c["id"] == "COL-0001")
        self.assertEqual(camila["ausencias"][0]["motivo"], "Ausencia programada")
        self.assertNotIn("Permiso administrativo", repr(vista["tareas"]))

    def test_gerencia_ve_todo_y_solo_nivel_1_ve_los_tratamientos(self):
        vista = self.vista(cargo="Gerente Comercial")
        self.assertIn("Carlos Silva Mendoza", [c["deudor"]["nombre"] for c in vista["casos"]])
        self.assertEqual(vista["tratamientos"], [])
        self.assertTrue(self.vista(cargo="Gerente General")["sesion"]["permisos"]["ver_tratamientos"])


class TestNotificaciones(unittest.TestCase):
    def setUp(self):
        self.reloj = Reloj()
        self.servicio = servicio_de_prueba(self.reloj)
        self.repo = self.servicio.repo

    def test_la_carga_del_sandbox_no_notifica(self):
        self.assertEqual(self.repo.listar("notificaciones"), [])
        self.assertEqual(self.repo.listar("correos"), [])

    def test_caso_nuevo_notifica_a_responsables_y_titulares_con_correo_sin_datos_del_deudor(self):
        respuesta = self.servicio.crear_caso({
            "rol_causa": "C-7001-2026", "tribunal": "1° Juzgado Civil de Santiago", "deudor_nombre": "Ana Pérez Rojas",
            "deudor_rut": "12.345.678-5", "mandante": "Forum", "monto_deuda": "3000000", "bien_tipo": "Vehículo",
            "bien_descripcion": "Automóvil", "bien_patente": "ZZ-YY-11", "estado_comercial": "En negociación",
            "estado_judicial": "Orden de incautación vigente", "responsable_comercial": "COL-0003",
            "responsable_judicial": "COL-0007", "fecha_diligencia": "",
        }, {"monto": 500000}, "Gerencia")
        tareas = [t for t in self.repo.listar("tareas") if t["caso_id"] == respuesta["caso"]["id"]]
        notificadas = {n["tarea_id"] for n in self.repo.listar("notificaciones") if n["tipo"] == "asignacion"}
        self.assertEqual(notificadas, {t["id"] for t in tareas})
        titulares = [n for n in self.repo.listar("notificaciones") if n["tipo"] == "titular"]
        self.assertEqual(len(titulares), 2)
        correos = self.repo.listar("correos")
        self.assertTrue(all(c["para"].endswith("@cobgestion.cl") and c["estado"] == "simulado" for c in correos))
        self.assertTrue(any(c["asunto"].startswith("[CRÍTICA]") for c in correos))
        for dato in ("Ana Pérez Rojas", "12.345.678-5", "ZZ-YY-11"):
            self.assertNotIn(dato, repr(correos) + repr(self.repo.listar("notificaciones")))

    def test_reasignar_avisa_al_nuevo_y_al_anterior(self):
        _, tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        tarea = tareas["Comercial"]
        anterior = tarea["responsable_id"]
        self.servicio.reasignar_tarea(tarea["id"], "Prueba", "Gerencia")
        tipos = {(n["tipo"], n["usuario_id"]) for n in self.repo.listar("notificaciones")}
        self.assertIn(("reasignacion", usuario_de(self.servicio, tarea["responsable_id"])["id"]), tipos)
        self.assertIn(("tarea_retirada", usuario_de(self.servicio, anterior)["id"]), tipos)

    def test_tarea_vencida_avisa_a_la_gerencia_del_area(self):
        _, tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        self.reloj.avanzar(hours=5)   # la tarea judicial crítica tiene 4 h
        self.servicio.escanear()
        gerente = usuario_de(self.servicio, cargo="Gerente Judicial")
        vencidas = [n for n in self.repo.listar("notificaciones") if n["tipo"] == "vencida"]
        self.assertIn(gerente["id"], {n["usuario_id"] for n in vencidas})

    def test_marcar_como_leidas(self):
        _, tareas = tareas_del_caso(self.servicio, "CASO-1052", "EC-01")
        self.servicio.reasignar_tarea(tareas["Comercial"]["id"], "Prueba", "Gerencia")
        usuario = usuario_de(self.servicio, self.repo.obtener("tareas", tareas["Comercial"]["id"])["responsable_id"])
        self.assertEqual(self.servicio.leer_notificaciones(usuario["id"])["marcadas"], 1)
        vista = vista_para(self.repo, actor_desde(self.repo, usuario["id"]), self.servicio.estado())
        self.assertEqual(vista["notificaciones_sin_leer"], 0)


if __name__ == "__main__":
    unittest.main()
