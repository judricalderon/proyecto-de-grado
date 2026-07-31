import importlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

FUNCTIONS = Path(__file__).resolve().parents[1] / "functions"

def load(domain):
    for name in ("app", "service", "repository", "models"):
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
    def setUp(self):self.app,self.repo=load("usuarios")
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

class PropuestasTest(unittest.TestCase):
    def setUp(self):self.app,self.repo=load("propuestas")
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
    def test_inexistente_invalido_json_y_ruta(self):
        self.assertEqual(call(self.app,"GET","/propuestas/X",params={"id":"X"})[0],404)
        self.assertEqual(call(self.app,"POST","/propuestas",{"titulo":"a","descripcion":"b"})[0],400)
        self.assertEqual(call(self.app,"POST","/propuestas","{")[0],400)
        self.assertEqual(call(self.app,"GET","/otra")[0],404)

class CatalogosTest(unittest.TestCase):
    def setUp(self):self.app,self.repo=load("catalogos")
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

class ProgresoTest(unittest.TestCase):
    def setUp(self):self.app,self.repo=load("progreso")
    def test_crear_actualizar_y_validar(self):
        base={"id_fase":"FASE-001","estado":"NO_INICIADA","porcentaje_avance":0}
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/progreso",base,{"id_propuesta":"PROP-001"})[0],201)
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/progreso",base,{"id_propuesta":"PROP-001"})[0],409)
        status,x=call(self.app,"PUT","/propuestas/PROP-001/progreso/FASE-001",{"estado":"COMPLETADA","porcentaje_avance":100},{"id_propuesta":"PROP-001","id_fase":"FASE-001"});self.assertEqual(status,200);self.assertIsNotNone(x["data"]["fecha_cierre"])
        self.assertEqual(call(self.app,"PUT","/propuestas/PROP-001/progreso/FASE-001",{"estado":"NO_INICIADA","porcentaje_avance":0},{"id_propuesta":"PROP-001","id_fase":"FASE-001"})[0],409)
        self.assertEqual(call(self.app,"PUT","/propuestas/PROP-001/progreso/FASE-001",{"estado":"EN_PROGRESO","porcentaje_avance":100},{"id_propuesta":"PROP-001","id_fase":"FASE-001"})[0],400)
        self.assertEqual(call(self.app,"POST","/propuestas/PROP-001/progreso",{"id_fase":"FASE-002","estado":"COMPLETADA","porcentaje_avance":50},{"id_propuesta":"PROP-001"})[0],400)

class EvaluacionesDocumentosTest(unittest.TestCase):
    def test_evaluacion_mas_reciente(self):
        app,repo=load("evaluaciones");data={"nivel_claridad":5,"nivel_argumentacion":4,"nivel_coherencia":5,"fortalezas":"Claridad","aspectos_por_fortalecer":"Fuentes"};params={"id_propuesta":"PROP-001","id_fase":"FASE-001"}
        self.assertEqual(call(app,"POST","/propuestas/PROP-001/fases/FASE-001/evaluaciones",data,params)[0],201)
        self.assertEqual(call(app,"GET","/propuestas/PROP-001/fases/FASE-001/evaluaciones/ultima",params=params)[0],200)
        self.assertEqual(call(app,"POST","/propuestas/PROP-001/fases/FASE-001/evaluaciones",{**data,"nivel_claridad":6},params)[0],400)
    def test_documentos_metadatos(self):
        app,repo=load("documentos");data={"tipo_documento":"ANEXO","nombre_archivo":"anexo.pdf","ruta":"temporal/anexo.pdf"};params={"id_propuesta":"PROP-001"}
        status,x=call(app,"POST","/propuestas/PROP-001/documentos",data,params);self.assertEqual(status,201);did=x["data"]["id"]
        self.assertEqual(call(app,"GET",f"/documentos/{did}",params={"id":did})[0],200)
        self.assertEqual(call(app,"PUT",f"/documentos/{did}",{"nombre_archivo":"nuevo.pdf"},{"id":did})[0],200)
        self.assertEqual(call(app,"DELETE",f"/documentos/{did}",params={"id":did})[0],204)

if __name__=="__main__":unittest.main()
