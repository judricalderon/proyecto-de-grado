from datetime import datetime,timezone
from uuid import uuid4
import repository as r
from models import EvaluacionIn
class DomainError(Exception):
 def __init__(self,m,c,s=400):super().__init__(m);self.message=m;self.code=c;self.status=s
def refs(pid,fid=None):
 if pid not in r.PROPOSALS:raise DomainError("Propuesta no encontrada","PROPOSAL_NOT_FOUND",404)
 if fid and fid not in r.PHASES:raise DomainError("Fase no encontrada","PHASE_NOT_FOUND",404)
def create(pid,fid,data):
 refs(pid,fid);m=EvaluacionIn.model_validate(data);x={"id":str(uuid4()),"id_propuesta":pid,"id_fase":fid,**m.model_dump(),"fecha_evaluacion":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")};r.items.append(x);return x
def get(i):
 x=r.get(i)
 if not x:raise DomainError("Evaluación no encontrada","EVALUATION_NOT_FOUND",404)
 return x
def latest(pid,fid):
 refs(pid,fid);xs=[x for x in r.items if x["id_propuesta"]==pid and x["id_fase"]==fid]
 if not xs:raise DomainError("Evaluación no encontrada","EVALUATION_NOT_FOUND",404)
 return max(xs,key=lambda x:x["fecha_evaluacion"])
