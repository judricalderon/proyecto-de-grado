import importlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

FUNCTIONS = Path(__file__).resolve().parents[1] / "functions"

def load(domain):
    for name in ("app", "service", "repository", "models", "database"):
        sys.modules.pop(name, None)
    path = str(FUNCTIONS / domain)
    sys.path.insert(0, path)
    try:
        app = importlib.import_module("app")
        repository = importlib.import_module("repository")
        repository.reset()
        return app, repository
    finally:
        sys.path.remove(path)

def event(method, path, body=None, params=None, query=None):
    value={"requestContext":{"http":{"method":method}},"rawPath":path,"pathParameters":params,"queryStringParameters":query}
    if body is not None:value["body"]=json.dumps(body) if isinstance(body,dict) else body
    return value
def call(app,method,path,body=None,params=None,query=None):
    result=app.lambda_handler(event(method,path,body,params,query),None)
    return result["statusCode"], json.loads(result["body"]) if result.get("body") else None

class UsuariosTest(unittest.TestCase):
    def setUp(self):
        self.app,self.repo=load("usuarios")
        items = [
            {"id":"USR-001","nombre":"Ana Estudiante","correo":"ana@example.com","tipo_usuario":"ESTUDIANTE","estado":"ACTIVO","fecha_creacion":"2026-07-28T19:00:00Z","fecha_ultimo_acceso":None},
            {"id":"USR-002","nombre":"Estudiante Sin Propuesta","correo":"sin@example.com","tipo_usuario":"ESTUDIANTE","estado":"ACTIVO","fecha_creacion":"2026-07-28T19:00:00Z","fecha_ultimo_acceso":None},
            {"id":"USR-010","nombre":"Diego Docente","correo":"diego@example.com","tipo_usuario":"DOCENTE","estado":"ACTIVO","fecha_creacion":"2026-07-28T19:00:00Z","fecha_ultimo_acceso":None}
        ]
        def all_items(filters=None):
            result=list(items);filters=filters or {}
            if filters.get("correo"):result=[x for x in result if x["correo"].lower()==filters["correo"].lower()]
            for key in ("tipo_usuario","estado"):
                if filters.get(key):result=[x for x in result if x[key]==filters[key]]
            return result
        self.repo.all = all_items
        self.repo.get = lambda item_id: next((x for x in items if x["id"] == item_id), None)
        self.repo.proposals_for_student=lambda item_id:([{"id":"PROP-001","titulo_tentativo":"Propuesta","descripcion_inicial":"Descripción extensa","estado_general":"BORRADOR","fecha_creacion":"2026-01-01T00:00:00Z","fecha_actualizacion":"2026-01-01T00:00:00Z"}] if item_id=="USR-001" else [])
        def add(item):
            if any(x["correo"] == item["correo"] for x in items): raise self.repo.DuplicateEmailError()
            items.append(item); return item
        def update(item_id, values):
            item=self.repo.get(item_id)
            if not item:return None
            if "correo" in values and any(x["correo"] == values["correo"] and x["id"] != item_id for x in items):raise self.repo.DuplicateEmailError()
            item.update(values);return item
        def deactivate(item_id):
            item=self.repo.get(item_id)
            if item:item["estado"]="INACTIVO"
            return item
        self.repo.add=add;self.repo.update=update;self.repo.deactivate=deactivate
    def test_crud_filtro_y_desactivacion(self):
        status,created=call(self.app,"POST","/usuarios",{"nombre":"Nuevo Usuario","correo":"nuevo@example.com","tipo_usuario":"ESTUDIANTE"})
        self.assertEqual(status,201);uid=created["data"]["id"]
        self.assertEqual(call(self.app,"GET",f"/usuarios/{uid}",params={"id":uid})[0],200)
        self.assertEqual(call(self.app,"PUT",f"/usuarios/{uid}",{"nombre":"Nombre Editado"},{"id":uid})[1]["data"]["nombre"],"Nombre Editado")
        self.assertEqual(call(self.app,"GET","/usuarios",query={"tipo_usuario":"ESTUDIANTE"})[0],200)
        self.assertEqual(call(self.app,"DELETE",f"/usuarios/{uid}",params={"id":uid})[1]["data"]["estado"],"INACTIVO")
    def test_inexistente_validacion_y_correo_unico(self):
        self.assertEqual(call(self.app,"GET","/usuarios/X",params={"id":"X"})[0],404)
        self.assertEqual(call(self.app,"POST","/usuarios",{"nombre":"A","correo":"mal","tipo_usuario":"NO"})[0],400)
        self.assertEqual(call(self.app,"POST","/usuarios",{"nombre":"Otra Ana","correo":"ana@example.com","tipo_usuario":"ESTUDIANTE"})[0],409)
    def test_json_ruta_y_error_inesperado(self):
        self.assertEqual(call(self.app,"POST","/usuarios","{")[0],400)
        self.assertEqual(call(self.app,"GET","/desconocida")[0],404)
        with patch.object(self.app.service,"list_items",side_effect=RuntimeError("interno")):
            self.assertEqual(call(self.app,"GET","/usuarios")[0],500)
    def test_filtros_correo_y_propuestas_estudiante(self):
        self.assertEqual(call(self.app,"GET","/usuarios",query={"correo":"ANA@EXAMPLE.COM"})[1]["count"],1)
        self.assertEqual(call(self.app,"GET","/usuarios",query={"correo":"missing@example.com"})[1]["count"],0)
        self.assertEqual(call(self.app,"GET","/usuarios",query={"correo":"ana@example.com","estado":"ACTIVO"})[1]["count"],1)
        self.assertEqual(call(self.app,"GET","/usuarios",query={"correo":"ana@example.com","tipo_usuario":"DOCENTE"})[1]["count"],0)
        status,result=call(self.app,"GET","/usuarios/USR-001/propuestas",params={"usuarioId":"USR-001"})
        self.assertEqual(status,200);self.assertEqual(result["count"],1)
        self.assertEqual(call(self.app,"GET","/usuarios/USR-002/propuestas",params={"usuarioId":"USR-002"})[1]["count"],0)
        self.assertEqual(call(self.app,"GET","/usuarios/NO/propuestas",params={"usuarioId":"NO"})[1]["code"],"USER_NOT_FOUND")
        self.assertEqual(call(self.app,"GET","/usuarios/USR-010/propuestas",params={"usuarioId":"USR-010"})[1]["code"],"INVALID_USER_TYPE")

class PropuestasTest(unittest.TestCase):
    def setUp(self):
        self.app,self.repo=load("propuestas")
        proposals=[{"id":"PROP-001","titulo_tentativo":"Sistema de acompañamiento","descripcion_inicial":"Descripción suficientemente larga","estado_general":"BORRADOR","fecha_creacion":"2026-07-28T19:00:00Z","fecha_actualizacion":"2026-07-28T19:00:00Z"}]
        students=[{"id":"REL-001","id_propuesta":"PROP-001","id_estudiante":"USR-001"}]
        directors=[]
        users={"USR-001":{"id":"USR-001","tipo_usuario":"ESTUDIANTE","estado":"ACTIVO"},"USR-002":{"id":"USR-002","tipo_usuario":"ESTUDIANTE","estado":"ACTIVO"},"USR-010":{"id":"USR-010","tipo_usuario":"DOCENTE","estado":"ACTIVO"},"USR-X":{"id":"USR-X","tipo_usuario":"ESTUDIANTE","estado":"INACTIVO"},"DOC-X":{"id":"DOC-X","tipo_usuario":"DOCENTE","estado":"INACTIVO"}}
        self.repo.all_proposals=lambda:proposals
        self.repo.get_proposal=lambda pid:next((x for x in proposals if x["id"]==pid),None)
        self.repo.add_proposal=lambda item:(proposals.append(item) or item)
        def update_proposal(pid,values,stamp):
            item=self.repo.get_proposal(pid)
            if item:item.update(values);item["fecha_actualizacion"]=stamp
            return item
        self.repo.update_proposal=update_proposal
        self.repo.close_proposal=lambda pid,stamp:update_proposal(pid,{"estado_general":"CERRADA"},stamp)
        self.repo.get_user=lambda uid:users.get(uid)
        self.repo.list_students=lambda pid:[users[x["id_estudiante"]] for x in students if x["id_propuesta"]==pid]
        def add_student(item):
            if any(x["id_propuesta"]==item["id_propuesta"] and x["id_estudiante"]==item["id_estudiante"] for x in students):raise self.repo.DuplicateStudentError()
            students.append(item);return item
        def remove_student(pid,uid):
            relation=next((x for x in students if x["id_propuesta"]==pid and x["id_estudiante"]==uid),None)
            if not relation:raise self.repo.AssignmentNotFoundError()
            proposal=self.repo.get_proposal(pid)
            if len([x for x in students if x["id_propuesta"]==pid])==1 and proposal["estado_general"]!="BORRADOR":raise self.repo.LastStudentRequiredError()
            students.remove(relation)
        self.repo.add_student=add_student;self.repo.remove_student=remove_student
        def active_director(pid):
            relation=next((x for x in directors if x["id_propuesta"]==pid and x["estado"]=="ACTIVO"),None)
            return users.get(relation["id_docente"]) if relation else None
        self.repo.get_active_director=active_director
        def add_director(item):
            if active_director(item["id_propuesta"]):raise self.repo.ActiveDirectorError()
            directors.append(item);return item
        def deactivate_director(pid):
            item=next((x for x in directors if x["id_propuesta"]==pid and x["estado"]=="ACTIVO"),None)
            if item:item["estado"]="INACTIVO"
            return item
        self.repo.add_director=add_director;self.repo.deactivate_director=deactivate_director
    def test_compatibilidad_crud(self):
        status,created=call(self.app,"POST","/propuestas",{"titulo":"Nueva propuesta","descripcion":"Descripción suficientemente larga","estudianteId":"USR-001"})
        self.assertEqual(status,201);pid=created["data"]["id"]
        self.assertEqual(call(self.app,"GET",f"/propuestas/{pid}",params={"id":pid})[0],200)
        updated=call(self.app,"PUT",f"/propuestas/{pid}",{"titulo_tentativo":"Título actualizado"},{"id":pid})
        self.assertEqual(updated[1]["data"]["titulo_tentativo"],"Título actualizado")
        self.assertEqual(call(self.app,"DELETE",f"/propuestas/{pid}",params={"id":pid})[1]["data"]["estado_general"],"CERRADA")
    def test_estudiantes_y_director(self):
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/estudiantes",{"id_estudiante":"USR-002"},{"id_propuesta":"PROP-001"})[0],201)
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/estudiantes",{"id_estudiante":"USR-002"},{"id_propuesta":"PROP-001"})[0],409)
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/estudiantes",{"id_estudiante":"USR-010"},{"id_propuesta":"PROP-001"})[0],409)
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/director",{"id_docente":"USR-010"},{"id_propuesta":"PROP-001"})[0],201)
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/director",{"id_docente":"USR-010"},{"id_propuesta":"PROP-001"})[0],409)
        self.assertEqual(call(self.app,"DELETE","/propuestas/PROP-001/director",params={"id_propuesta":"PROP-001"})[1]["data"]["estado"],"INACTIVO")
    def test_lecturas_devuelven_perfiles(self):
        params={"id_propuesta":"PROP-001"}
        students_result=call(self.app,"GET","/propuestas/PROP-001/estudiantes",params=params)[1]
        self.assertEqual(students_result["data"][0]["id"],"USR-001")
        self.assertNotIn("id_propuesta",students_result["data"][0])
        self.assertIsNone(call(self.app,"GET","/propuestas/PROP-001/director",params=params)[1]["data"])
        call(self.app,"POST","/propuestas/PROP-001/director",{"id_docente":"USR-010"},params)
        director=call(self.app,"GET","/propuestas/PROP-001/director",params=params)[1]["data"]
        self.assertEqual(director["id"],"USR-010");self.assertEqual(director["tipo_usuario"],"DOCENTE")
    def test_inexistente_invalido_json_y_ruta(self):
        self.assertEqual(call(self.app,"GET","/propuestas/X",params={"id":"X"})[0],404)
        self.assertEqual(call(self.app,"POST","/propuestas",{"titulo":"a","descripcion":"b"})[0],400)
        self.assertEqual(call(self.app,"POST","/propuestas","{")[0],400)
        self.assertEqual(call(self.app,"GET","/otra")[0],404)
    def test_usuarios_invalidos_e_inactivos(self):
        params={"id_propuesta":"PROP-001"}
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/estudiantes",{"id_estudiante":"NO-EXISTE"},params)[1]["code"],"USER_NOT_FOUND")
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/estudiantes",{"id_estudiante":"USR-010"},params)[1]["code"],"INVALID_USER_TYPE")
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/estudiantes",{"id_estudiante":"USR-X"},params)[1]["code"],"USER_INACTIVE")
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/director",{"id_docente":"USR-001"},params)[1]["code"],"INVALID_USER_TYPE")
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/director",{"id_docente":"DOC-X"},params)[1]["code"],"USER_INACTIVE")

class CatalogosTest(unittest.TestCase):
    def setUp(self):
        self.app,self.repo=load("catalogos")
        modules=[{"id":"MOD-001","nombre":"Desarrollo de propuestas de proyectos","descripcion":"Módulo inicial","orden":1,"activo":True}]
        phases=[{"id":f"FASE-{i:03}","id_modulo":"MOD-001","nombre":f"Fase {i}","descripcion":f"Fase {i}","orden":i,"activo":True} for i in range(1,8)]
        agents=[];collections={"modulos":modules,"fases":phases,"agentes":agents}
        self.repo.list_items=lambda kind,module_id=None:[x for x in collections[kind] if module_id is None or x.get("id_modulo")==module_id]
        self.repo.get=lambda kind,item_id:next((x for x in collections[kind] if x["id"]==item_id),None)
        self.repo.active_order_exists=lambda kind,order,module_id=None,exclude_id=None:any(x["activo"] and x["orden"]==order and x["id"]!=exclude_id and (kind!="fases" or x["id_modulo"]==module_id) for x in collections[kind])
        self.repo.active_agent_name_exists=lambda name,exclude_id=None:any(x["activo"] and x["nombre"].lower()==name.lower() and x["id"]!=exclude_id for x in agents)
        self.repo.module_has_active_phases=lambda module_id:any(x["activo"] and x["id_modulo"]==module_id for x in phases)
        def add(kind,item):collections[kind].append(item);return item
        def update(kind,item_id,values):
            item=self.repo.get(kind,item_id)
            if item:item.update(values)
            return item
        self.repo.add=add;self.repo.update=update;self.repo.deactivate=lambda kind,item_id:update(kind,item_id,{"activo":False})
    def test_modulo_conflicto_y_desactivacion(self):
        self.assertEqual(call(self.app,"POST","/modulos",{"nombre":"Duplicado","descripcion":"D","orden":1})[0],409)
        status,x=call(self.app,"POST","/modulos",{"nombre":"Segundo","descripcion":"D","orden":2});self.assertEqual(status,201)
        mid=x["data"]["id"];self.assertEqual(call(self.app,"PUT",f"/modulos/{mid}",{"nombre":"Editado"},{"id":mid})[0],200)
        self.assertEqual(call(self.app,"DELETE",f"/modulos/{mid}",params={"id":mid})[1]["data"]["activo"],False)
        self.assertEqual(call(self.app,"DELETE","/modulos/MOD-001",params={"id":"MOD-001"})[0],409)
    def test_fase_y_agente_unicos(self):
        self.assertEqual(call(self.app,"POST","/fases",{"id_modulo":"MOD-001","nombre":"Otra","descripcion":"D","orden":1})[0],409)
        agent={"nombre":"Orientador","tipo_agente":"ORIENTADOR","descripcion":"Guía"}
        self.assertEqual(call(self.app,"POST","/agentes",agent)[0],201)
        self.assertEqual(call(self.app,"POST","/agentes",agent)[0],409)
    def test_listar_obtener_actualizar_y_desactivar_fase_agente(self):
        self.assertEqual(call(self.app,"GET","/modulos")[1]["count"],1)
        self.assertEqual(call(self.app,"GET","/modulos/MOD-001",params={"id":"MOD-001"})[0],200)
        self.assertEqual(call(self.app,"GET","/modulos/MOD-001/fases",params={"id_modulo":"MOD-001"})[1]["count"],7)
        self.assertEqual(call(self.app,"GET","/fases/NO",params={"id":"NO"})[0],404)
        created=call(self.app,"POST","/fases",{"id_modulo":"MOD-001","nombre":"Cierre","descripcion":"D","orden":8})[1]["data"]
        self.assertTrue(created["id"].startswith("FASE-"))
        self.assertEqual(call(self.app,"PUT",f"/fases/{created['id']}",{"descripcion":"Editada"},{"id":created["id"]})[1]["data"]["descripcion"],"Editada")
        self.assertFalse(call(self.app,"DELETE",f"/fases/{created['id']}",params={"id":created["id"]})[1]["data"]["activo"])
        self.assertEqual(call(self.app,"POST","/fases",{"id_modulo":"NO","nombre":"X","descripcion":"D","orden":1})[1]["code"],"MODULE_NOT_ACTIVE")
        agent=call(self.app,"POST","/agentes",{"nombre":"Evaluador","tipo_agente":"EVALUADOR","descripcion":"D"})[1]["data"]
        self.assertEqual(call(self.app,"PUT",f"/agentes/{agent['id']}",{"descripcion":"Editado"},{"id":agent["id"]})[0],200)
        self.assertFalse(call(self.app,"DELETE",f"/agentes/{agent['id']}",params={"id":agent["id"]})[1]["data"]["activo"])
        self.assertEqual(call(self.app,"POST","/agentes",{"nombre":"Inválido","tipo_agente":"OTRO","descripcion":"D"})[0],400)

class ProgresoTest(unittest.TestCase):
    def setUp(self):
        self.app,self.repo=load("progreso");items=[];proposals={"PROP-001"};phases={f"FASE-{i:03}":{"id":f"FASE-{i:03}","activo":True} for i in range(1,8)};phases["FASE-X"]={"id":"FASE-X","activo":False}
        self.repo.list_by_proposal=lambda pid:[x for x in items if x["id_propuesta"]==pid]
        self.repo.get=lambda pid,fid:next((x for x in items if x["id_propuesta"]==pid and x["id_fase"]==fid),None)
        self.repo.proposal_exists=lambda pid:pid in proposals
        self.repo.get_phase=lambda fid:phases.get(fid)
        def add(item):
            if self.repo.get(item["id_propuesta"],item["id_fase"]):raise self.repo.DuplicateProgressError()
            items.append(item);return item
        def update(pid,fid,values):
            item=self.repo.get(pid,fid)
            if item:item.update(values)
            return item
        self.repo.add=add;self.repo.update=update
    def test_crear_actualizar_y_validar(self):
        base={"id_fase":"FASE-001","estado":"NO_INICIADA","porcentaje_avance":0}
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/progreso",base,{"id_propuesta":"PROP-001"})[0],201)
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/progreso",base,{"id_propuesta":"PROP-001"})[0],409)
        status,x=call(self.app,"PUT","/propuestas/PROP-001/progreso/FASE-001",{"estado":"COMPLETADA","porcentaje_avance":100},{"id_propuesta":"PROP-001","id_fase":"FASE-001"});self.assertEqual(status,200);self.assertIsNotNone(x["data"]["fecha_cierre"])
        self.assertEqual(call(self.app,"PUT","/propuestas/PROP-001/progreso/FASE-001",{"estado":"NO_INICIADA","porcentaje_avance":0},{"id_propuesta":"PROP-001","id_fase":"FASE-001"})[0],409)
        self.assertEqual(call(self.app,"PUT","/propuestas/PROP-001/progreso/FASE-001",{"estado":"EN_PROGRESO","porcentaje_avance":100},{"id_propuesta":"PROP-001","id_fase":"FASE-001"})[0],400)
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/progreso",{"id_fase":"FASE-002","estado":"COMPLETADA","porcentaje_avance":50},{"id_propuesta":"PROP-001"})[0],400)
    def test_listar_referencias_fechas_e_inexistentes(self):
        no_iniciada={"id_fase":"FASE-001","estado":"NO_INICIADA","porcentaje_avance":0};params={"id_propuesta":"PROP-001"}
        created=call(self.app,"POST","/propuestas/PROP-001/progreso",no_iniciada,params)[1]["data"]
        self.assertIsNone(created["fecha_inicio"]);self.assertIsNone(created["fecha_cierre"])
        self.assertEqual(call(self.app,"GET","/propuestas/PROP-001/progreso",params=params)[1]["count"],1)
        self.assertEqual(call(self.app,"GET","/propuestas/PROP-001/progreso/FASE-001",params={**params,"id_fase":"FASE-001"})[0],200)
        self.assertEqual(call(self.app,"GET","/propuestas/PROP-001/progreso/FASE-002",params={**params,"id_fase":"FASE-002"})[1]["code"],"PROGRESS_NOT_FOUND")
        self.assertEqual(call(self.app,"POST","/propuestas/NO/progreso",no_iniciada,{"id_propuesta":"NO"})[1]["code"],"PROPOSAL_NOT_FOUND")
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/progreso",{"id_fase":"NO","estado":"NO_INICIADA","porcentaje_avance":0},params)[1]["code"],"PHASE_NOT_FOUND")
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/progreso",{"id_fase":"FASE-X","estado":"NO_INICIADA","porcentaje_avance":0},params)[1]["code"],"PHASE_NOT_FOUND")
        progressing=call(self.app,"POST","/propuestas/PROP-001/progreso",{"id_fase":"FASE-002","estado":"EN_PROGRESO","porcentaje_avance":50},params)[1]["data"]
        self.assertIsNotNone(progressing["fecha_inicio"])
        completed=call(self.app,"POST","/propuestas/PROP-001/progreso",{"id_fase":"FASE-003","estado":"COMPLETADA","porcentaje_avance":100},params)[1]["data"]
        self.assertIsNotNone(completed["fecha_inicio"]);self.assertIsNotNone(completed["fecha_cierre"])

class EvaluacionesDocumentosTest(unittest.TestCase):
    def test_evaluacion_mas_reciente(self):
        app,repo=load("evaluaciones");items=[]
        repo.proposal_exists=lambda pid:pid=="PROP-001"
        repo.get_phase=lambda fid:{"id":fid,"activo":True} if fid=="FASE-001" else None
        repo.list_by_proposal=lambda pid,fid=None:[x for x in items if x["id_propuesta"]==pid and (fid is None or x["id_fase"]==fid)]
        repo.get=lambda item_id:next((x for x in items if x["id"]==item_id),None)
        repo.latest=lambda pid,fid:max(repo.list_by_proposal(pid,fid),key=lambda x:x["fecha_evaluacion"],default=None)
        repo.add=lambda item:items.append(item) or item
        data={"nivel_claridad":5,"nivel_argumentacion":4,"nivel_coherencia":5,"fortalezas":"Claridad","aspectos_por_fortalecer":"Fuentes"};params={"id_propuesta":"PROP-001","id_fase":"FASE-001"}
        created=call(app,"POST","/propuestas/PROP-001/fases/FASE-001/evaluaciones",data,params)
        self.assertEqual(created[0],201);self.assertEqual(created[1]["data"]["observaciones"],"")
        self.assertEqual(call(app,"GET",f"/evaluaciones/{created[1]['data']['id']}",params={"id":created[1]["data"]["id"]})[0],200)
        minimum={**data,"nivel_claridad":1,"nivel_argumentacion":1,"nivel_coherencia":1}
        self.assertEqual(call(app,"POST","/propuestas/PROP-001/fases/FASE-001/evaluaciones",minimum,params)[0],201)
        self.assertEqual(call(app,"GET","/propuestas/PROP-001/fases/FASE-001/evaluaciones/ultima",params=params)[0],200)
        self.assertEqual(call(app,"GET","/propuestas/PROP-001/evaluaciones",params={"id_propuesta":"PROP-001"})[1]["count"],2)
        self.assertEqual(call(app,"GET","/propuestas/PROP-001/fases/FASE-001/evaluaciones",params=params)[1]["count"],2)
        self.assertEqual(call(app,"POST","/propuestas/NO/fases/FASE-001/evaluaciones",data,{"id_propuesta":"NO","id_fase":"FASE-001"})[1]["code"],"PROPOSAL_NOT_FOUND")
        self.assertEqual(call(app,"POST","/propuestas/PROP-001/fases/NO/evaluaciones",data,{"id_propuesta":"PROP-001","id_fase":"NO"})[1]["code"],"PHASE_NOT_FOUND")
        self.assertEqual(call(app,"POST","/propuestas/PROP-001/fases/FASE-001/evaluaciones",{**data,"nivel_claridad":0},params)[0],400)
        self.assertEqual(call(app,"POST","/propuestas/PROP-001/fases/FASE-001/evaluaciones",{**data,"nivel_claridad":6},params)[0],400)
    def test_documentos_metadatos(self):
        app,repo=load("documentos");items=[]
        repo.proposal_exists=lambda pid:pid=="PROP-001"
        repo.list_by_proposal=lambda pid:[x for x in items if x["id_propuesta"]==pid]
        repo.get=lambda item_id:next((x for x in items if x["id"]==item_id),None)
        repo.add=lambda item:items.append(item) or item
        def update(item_id,values):
            item=repo.get(item_id)
            if item:item.update(values)
            return item
        repo.update=update
        def delete(item_id):
            item=repo.get(item_id)
            if item:items.remove(item)
            return item
        repo.delete=delete
        data={"tipo_documento":"ANEXO","nombre_archivo":"anexo.pdf","ruta":"temporal/anexo.pdf"};params={"id_propuesta":"PROP-001"}
        status,x=call(app,"POST","/propuestas/PROP-001/documentos",data,params);self.assertEqual(status,201);did=x["data"]["id"]
        self.assertEqual(call(app,"GET","/propuestas/PROP-001/documentos",params=params)[1]["count"],1)
        self.assertEqual(call(app,"GET",f"/documentos/{did}",params={"id":did})[0],200)
        self.assertEqual(call(app,"PUT",f"/documentos/{did}",{"nombre_archivo":"nuevo.pdf"},{"id":did})[0],200)
        self.assertEqual(call(app,"DELETE",f"/documentos/{did}",params={"id":did})[0],204)
        self.assertEqual(call(app,"GET",f"/documentos/{did}",params={"id":did})[1]["code"],"DOCUMENT_NOT_FOUND")
        self.assertEqual(call(app,"DELETE","/documentos/NO",params={"id":"NO"})[1]["code"],"DOCUMENT_NOT_FOUND")
        self.assertEqual(call(app,"POST","/propuestas/NO/documentos",data,{"id_propuesta":"NO"})[1]["code"],"PROPOSAL_NOT_FOUND")
        self.assertEqual(call(app,"POST","/propuestas/PROP-001/documentos",{**data,"tipo_documento":"INVALIDO"},params)[0],400)
        for document_type in ("PROPUESTA","ACTA","ANEXO","INFORME","OTRO"):
            self.assertEqual(call(app,"POST","/propuestas/PROP-001/documentos",{**data,"tipo_documento":document_type},params)[0],201)

if __name__=="__main__":unittest.main()
