from datetime import datetime,timezone
from uuid import uuid4
import repository as r
from models import ProgresoIn,ProgresoUpdate
class DomainError(Exception):
 def __init__(self,m,c,s=400):super().__init__(m);self.message=m;self.code=c;self.status=s
def now():return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def refs(pid,fid):
 if pid not in r.PROPOSALS:raise DomainError("Propuesta no encontrada","PROPOSAL_NOT_FOUND",404)
 if fid not in r.PHASES:raise DomainError("Fase no encontrada","PHASE_NOT_FOUND",404)
def create(pid,data):
 m=ProgresoIn.model_validate(data);refs(pid,m.id_fase)
 if r.get(pid,m.id_fase):raise DomainError("El progreso ya existe","PROGRESS_ALREADY_EXISTS",409)
 stamp=now();x={"id":str(uuid4()),"id_propuesta":pid,**m.model_dump(mode="json"),"fecha_inicio":stamp if m.estado.value!="NO_INICIADA" else None,"fecha_ultima_actualizacion":stamp,"fecha_cierre":stamp if m.estado.value=="COMPLETADA" else None};r.items.append(x);return x
def get(pid,fid):
 refs(pid,fid);x=r.get(pid,fid)
 if not x:raise DomainError("Progreso no encontrado","PROGRESS_NOT_FOUND",404)
 return x
def update(pid,fid,data):
 x=get(pid,fid);m=ProgresoUpdate.model_validate(data)
 if x["estado"]=="COMPLETADA" and m.estado.value=="NO_INICIADA":raise DomainError("Use una acción explícita de reapertura","REOPEN_REQUIRED",409)
 stamp=now();x.update(m.model_dump(mode="json"));x["fecha_ultima_actualizacion"]=stamp
 if m.estado.value=="EN_PROGRESO" and not x["fecha_inicio"]:x["fecha_inicio"]=stamp
 if m.estado.value=="COMPLETADA":x["fecha_cierre"]=stamp
 return x
