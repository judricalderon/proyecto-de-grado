import json
from pydantic import ValidationError
import repository as r,service
def out(s,b):return {"statusCode":s,"headers":{"Content-Type":"application/json"},"body":json.dumps(b,ensure_ascii=False)}
def body(e):
 try:return json.loads(e.get("body")) if isinstance(e.get("body"),str) else e.get("body")
 except Exception:raise service.DomainError("JSON inválido","VALIDATION_ERROR")
def lambda_handler(e,c):
 try:
  request_context=e.get("requestContext",{});http_context=request_context.get("http",{})
  m=http_context.get("method","");path=e.get("rawPath","");stage=request_context.get("stage","");stage_prefix=f"/{stage}"
  if stage and path.startswith(stage_prefix+"/"):path=path[len(stage_prefix):]
  q=e.get("pathParameters") or {};pid=q.get("id_propuesta");fid=q.get("id_fase")
  if path=="/evaluaciones/health":return out(200,{"data":{"service":"evaluaciones","status":"ok"}})
  if path.startswith("/evaluaciones/") and m=="GET":return out(200,{"data":service.get(q.get("id"))})
  if path.endswith("/evaluaciones/ultima") and m=="GET":return out(200,{"data":service.latest(pid,fid)})
  if path.endswith("/evaluaciones"):
   if m=="POST":return out(201,{"message":"Evaluación creada correctamente","data":service.create(pid,fid,body(e))})
   service.refs(pid,fid);data=[x for x in r.items if x["id_propuesta"]==pid and (not fid or x["id_fase"]==fid)];return out(200,{"data":data,"count":len(data)})
  return out(404,{"error":"Ruta no encontrada","code":"ROUTE_NOT_FOUND","details":[]})
 except ValidationError as x:return out(400,{"error":"Datos de entrada inválidos","code":"VALIDATION_ERROR","details":[a["msg"] for a in x.errors()]})
 except service.DomainError as x:return out(x.status,{"error":x.message,"code":x.code,"details":[]})
 except Exception:return out(500,{"error":"Error interno del servidor","code":"INTERNAL_SERVER_ERROR","details":[]})
