import json
from pydantic import ValidationError
import repository as r, service
def response(s,b): return {"statusCode":s,"headers":{"Content-Type":"application/json"},"body":json.dumps(b,ensure_ascii=False)}
def payload(e):
 try: return json.loads(e.get("body")) if isinstance(e.get("body"),str) else e.get("body")
 except (json.JSONDecodeError,TypeError): raise service.DomainError("JSON inválido","VALIDATION_ERROR",400,["El cuerpo debe ser JSON válido"])
def lambda_handler(event,context):
 try:
  request_context=event.get("requestContext",{})
  http_context=request_context.get("http",{})
  method=http_context.get("method","")
  path=event.get("rawPath","")
  stage=request_context.get("stage","")
  stage_prefix=f"/{stage}"
  if stage and path.startswith(stage_prefix+"/"):
   path=path[len(stage_prefix):]
  q=event.get("pathParameters") or {}
  if method=="GET" and path=="/propuestas/health": return response(200,{"message":"Servicio de propuestas funcionando","service":"propuestas","status":"ok"})
  if path=="/propuestas":
   if method=="GET": return response(200,{"data":r.propuestas,"count":len(r.propuestas)})
   if method=="POST": return response(201,{"message":"Propuesta creada correctamente","data":service.create(payload(event))})
  pid=q.get("id") or q.get("id_propuesta")
  if path.endswith("/estudiantes"):
   if method=="GET":
    service.proposal(pid); data=[x for x in r.estudiantes if x["id_propuesta"]==pid];return response(200,{"data":data,"count":len(data)})
   if method=="POST": return response(201,{"message":"Estudiante asignado correctamente","data":service.add_student(pid,payload(event))})
  if "/estudiantes/" in path and method=="DELETE": service.remove_student(pid,q.get("id_estudiante"));return response(200,{"data":{"removed":True}})
  if path.endswith("/director"):
   if method=="GET": return response(200,{"data":service.director(pid)})
   if method=="POST": return response(201,{"message":"Director asignado correctamente","data":service.assign_director(pid,payload(event))})
   if method=="DELETE": return response(200,{"data":service.unassign_director(pid)})
  if path.startswith("/propuestas/"):
   if method=="GET": return response(200,{"data":service.proposal(pid)})
   if method=="PUT": return response(200,{"data":service.update(pid,payload(event))})
   if method=="DELETE": return response(200,{"data":service.close(pid)})
  return response(404,{"error":"Ruta no encontrada","code":"ROUTE_NOT_FOUND","details":[]})
 except ValidationError as e:return response(400,{"error":"Datos de entrada inválidos","code":"VALIDATION_ERROR","details":[x["msg"] for x in e.errors()]})
 except service.DomainError as e:return response(e.status,{"error":e.message,"code":e.code,"details":e.details})
 except Exception:return response(500,{"error":"Error interno del servidor","code":"INTERNAL_SERVER_ERROR","details":[]})
