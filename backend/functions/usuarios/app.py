import json
from pydantic import ValidationError
import service

def response(status, body): return {"statusCode":status,"headers":{"Content-Type":"application/json"},"body":json.dumps(body, ensure_ascii=False)}
def body(event):
    raw=event.get("body")
    if event.get("isBase64Encoded"): raise service.DomainError("El cuerpo codificado no está soportado", "INVALID_BODY")
    try: return json.loads(raw) if isinstance(raw,str) else raw
    except (json.JSONDecodeError,TypeError): raise service.DomainError("JSON inválido", "VALIDATION_ERROR", 400, ["El cuerpo debe ser JSON válido"])
def lambda_handler(event, context):
    try:
        request_context = event.get("requestContext", {})
        http_context = request_context.get("http", {})
        method = http_context.get("method", "")
        path = event.get("rawPath", "")
        stage = request_context.get("stage", "")
        stage_prefix = f"/{stage}"
        if stage and path.startswith(stage_prefix + "/"):
            path = path[len(stage_prefix):]
        params=event.get("pathParameters") or {}; query=event.get("queryStringParameters") or {}
        if method=="GET" and path=="/usuarios/health": return response(200,{"data":{"service":"usuarios","status":"ok"}})
        if path=="/usuarios" and method=="GET":
            data=service.list_items(query); return response(200,{"data":data,"count":len(data)})
        if path=="/usuarios" and method=="POST": return response(201,{"message":"Usuario creado correctamente","data":service.create(body(event))})
        if path.startswith("/usuarios/"):
            item_id=params.get("id")
            if method=="GET": return response(200,{"data":service.get_item(item_id)})
            if method=="PUT": return response(200,{"data":service.update(item_id,body(event))})
            if method=="DELETE": return response(200,{"data":service.deactivate(item_id)})
        return response(404,{"error":"Ruta no encontrada","code":"ROUTE_NOT_FOUND","details":[]})
    except ValidationError as error: return response(400,{"error":"Datos de entrada inválidos","code":"VALIDATION_ERROR","details":[x["msg"] for x in error.errors()]})
    except service.DomainError as error: return response(error.status,{"error":error.message,"code":error.code,"details":error.details})
    except Exception: return response(500,{"error":"Error interno del servidor","code":"INTERNAL_SERVER_ERROR","details":[]})
