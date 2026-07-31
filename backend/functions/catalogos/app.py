import json
from pydantic import ValidationError
import repository as r,service
def out(s,b):return {"statusCode":s,"headers":{"Content-Type":"application/json"},"body":json.dumps(b,ensure_ascii=False)}
def data(e):
 try:return json.loads(e.get("body")) if isinstance(e.get("body"),str) else e.get("body")
 except Exception:raise service.DomainError("JSON inválido","VALIDATION_ERROR")
def lambda_handler(e,c):
 try:
  request_context=e.get("requestContext",{});http_context=request_context.get("http",{})
  m=http_context.get("method","");path=e.get("rawPath","");stage=request_context.get("stage","");stage_prefix=f"/{stage}"
  if stage and path.startswith(stage_prefix+"/"):path=path[len(stage_prefix):]
  q=e.get("pathParameters") or {};kind="modulos" if path.startswith("/modulos") else "fases" if path.startswith("/fases") else "agentes" if path.startswith("/agentes") else None
  if path.endswith("/fases") and path.startswith("/modulos/"):
   items=[x for x in r.fases if x["id_modulo"]==q.get("id_modulo")];return out(200,{"data":items,"count":len(items)})
  if not kind:return out(404,{"error":"Ruta no encontrada","code":"ROUTE_NOT_FOUND","details":[]})
  items=getattr(r,kind);item_id=q.get("id")
  if path==f"/{kind}":
   if m=="GET":return out(200,{"data":items,"count":len(items)})
   if m=="POST":return out(201,{"message":"Recurso creado correctamente","data":service.create(kind,data(e))})
  if m=="GET":return out(200,{"data":service.get(kind,item_id)})
  if m=="PUT":return out(200,{"data":service.update(kind,item_id,data(e))})
  if m=="DELETE":return out(200,{"data":service.deactivate(kind,item_id)})
  return out(404,{"error":"Ruta no encontrada","code":"ROUTE_NOT_FOUND","details":[]})
 except ValidationError as x:return out(400,{"error":"Datos de entrada inválidos","code":"VALIDATION_ERROR","details":[a["msg"] for a in x.errors()]})
 except service.DomainError as x:return out(x.status,{"error":x.message,"code":x.code,"details":[]})
 except Exception:return out(500,{"error":"Error interno del servidor","code":"INTERNAL_SERVER_ERROR","details":[]})
