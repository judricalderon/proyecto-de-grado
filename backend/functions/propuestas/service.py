from datetime import datetime,timezone
from uuid import uuid4
import repository as r
from models import PropuestaCreate,PropuestaUpdate,EstudianteCreate,DirectorCreate
class DomainError(Exception):
 def __init__(self,m,c,s=400,d=None): super().__init__(m); self.message=m;self.code=c;self.status=s;self.details=d or []
def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def proposal(pid):
 p=r.get(r.propuestas,pid)
 if not p: raise DomainError("Propuesta no encontrada","PROPOSAL_NOT_FOUND",404)
 return p
def normalize(data):
 data=dict(data or {})
 if "titulo" in data: data.setdefault("titulo_tentativo",data["titulo"])
 if "descripcion" in data: data.setdefault("descripcion_inicial",data["descripcion"])
 return data
def create(data):
 m=PropuestaCreate.model_validate(normalize(data)); stamp=now(); p={"id":str(uuid4()),**m.model_dump(),"estado_general":"BORRADOR","fecha_creacion":stamp,"fecha_actualizacion":stamp}; r.propuestas.append(p); return p
def update(pid,data):
 p=proposal(pid); values=PropuestaUpdate.model_validate(normalize(data)).model_dump(exclude_none=True,mode="json");p.update(values);p["fecha_actualizacion"]=now();return p
def close(pid): p=proposal(pid);p["estado_general"]="CERRADA";p["fecha_actualizacion"]=now();return p
def user(uid,kind):
 u=r._U.get(uid)
 if not u: raise DomainError("Usuario no encontrado","USER_NOT_FOUND",404)
 if u["estado"]!="ACTIVO": raise DomainError("El usuario está inactivo","USER_INACTIVE",409)
 if u["tipo_usuario"]!=kind: raise DomainError("Tipo de usuario inválido","INVALID_USER_TYPE",409)
def add_student(pid,data):
 proposal(pid);m=EstudianteCreate.model_validate(data);user(m.id_estudiante,"ESTUDIANTE")
 if any(x["id_propuesta"]==pid and x["id_estudiante"]==m.id_estudiante for x in r.estudiantes): raise DomainError("El estudiante ya está asignado","STUDENT_ALREADY_ASSIGNED",409)
 rel={"id":str(uuid4()),"id_propuesta":pid,"id_estudiante":m.id_estudiante};r.estudiantes.append(rel);return rel
def remove_student(pid,uid):
 p=proposal(pid); rel=next((x for x in r.estudiantes if x["id_propuesta"]==pid and x["id_estudiante"]==uid),None)
 if not rel: raise DomainError("Asignación no encontrada","ASSIGNMENT_NOT_FOUND",404)
 total=sum(x["id_propuesta"]==pid for x in r.estudiantes)
 if total==1 and p["estado_general"]!="BORRADOR": raise DomainError("No se puede retirar el último estudiante","LAST_STUDENT_REQUIRED",409)
 r.estudiantes.remove(rel)
def assign_director(pid,data):
 proposal(pid);m=DirectorCreate.model_validate(data);user(m.id_docente,"DOCENTE")
 if any(x["id_propuesta"]==pid and x["estado"]=="ACTIVO" for x in r.directores): raise DomainError("La propuesta ya tiene director activo","ACTIVE_DIRECTOR_EXISTS",409)
 rel={"id":str(uuid4()),"id_propuesta":pid,"id_docente":m.id_docente,"fecha_asignacion":now(),"estado":"ACTIVO"};r.directores.append(rel);return rel
def director(pid): proposal(pid); return next((x for x in r.directores if x["id_propuesta"]==pid and x["estado"]=="ACTIVO"),None)
def unassign_director(pid):
 d=director(pid)
 if not d: raise DomainError("Director activo no encontrado","DIRECTOR_NOT_FOUND",404)
 d["estado"]="INACTIVO";return d
