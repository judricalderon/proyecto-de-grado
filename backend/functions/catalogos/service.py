from uuid import uuid4
import repository as r
from models import ModuloIn,FaseIn,AgenteIn
class DomainError(Exception):
 def __init__(self,m,c,s=400):super().__init__(m);self.message=m;self.code=c;self.status=s
def cfg(kind): return {"modulos":(r.modulos,ModuloIn,"MOD"),"fases":(r.fases,FaseIn,"FASE"),"agentes":(r.agentes,AgenteIn,"AG")}[kind]
def get(kind,i):
 x=r.get(cfg(kind)[0],i)
 if not x:raise DomainError("Recurso no encontrado","RESOURCE_NOT_FOUND",404)
 return x
def validate(kind,data,current=None):
 items,model,_=cfg(kind);m=model.model_validate(data);v=m.model_dump(mode="json")
 if kind=="modulos" and any(x["activo"] and x["orden"]==v["orden"] and x is not current for x in items):raise DomainError("Orden duplicado","ACTIVE_ORDER_CONFLICT",409)
 if kind=="fases":
  mod=r.get(r.modulos,v["id_modulo"])
  if not mod or not mod["activo"]:raise DomainError("Módulo inexistente o inactivo","MODULE_NOT_ACTIVE",409)
  if any(x["activo"] and x["id_modulo"]==v["id_modulo"] and x["orden"]==v["orden"] and x is not current for x in items):raise DomainError("Orden duplicado en el módulo","ACTIVE_ORDER_CONFLICT",409)
 if kind=="agentes" and any(x["activo"] and x["nombre"].lower()==v["nombre"].lower() and x is not current for x in items):raise DomainError("Nombre de agente duplicado","ACTIVE_NAME_CONFLICT",409)
 return v
def create(kind,data):
 items,_,prefix=cfg(kind);x={"id":f"{prefix}-{uuid4()}",**validate(kind,data)};items.append(x);return x
def update(kind,i,data):
 x=get(kind,i);merged={**x,**data};merged.pop("id",None);x.update(validate(kind,merged,x));return x
def deactivate(kind,i):
 x=get(kind,i)
 if kind=="modulos" and any(f["id_modulo"]==i and f["activo"] for f in r.fases):raise DomainError("El módulo tiene fases activas","MODULE_HAS_ACTIVE_PHASES",409)
 x["activo"]=False;return x
