from datetime import datetime,timezone
from uuid import uuid4
import repository as r
from models import DocumentoIn,DocumentoUpdate
class DomainError(Exception):
 def __init__(self,m,c,s=400):super().__init__(m);self.message=m;self.code=c;self.status=s
def create(pid,data):
 if pid not in r.PROPOSALS:raise DomainError("Propuesta no encontrada","PROPOSAL_NOT_FOUND",404)
 m=DocumentoIn.model_validate(data);x={"id":str(uuid4()),"id_propuesta":pid,**m.model_dump(mode="json"),"fecha_carga":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")};r.items.append(x);return x
def get(i):
 x=r.get(i)
 if not x:raise DomainError("Documento no encontrado","DOCUMENT_NOT_FOUND",404)
 return x
def update(i,data):x=get(i);x.update(DocumentoUpdate.model_validate(data).model_dump(exclude_none=True,mode="json"));return x
def delete(i):x=get(i);r.items.remove(x)
