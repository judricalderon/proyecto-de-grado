from datetime import datetime, timezone
from uuid import uuid4
import repository
from models import UsuarioCreate, UsuarioUpdate

class DomainError(Exception):
    def __init__(self, message, code, status=400, details=None):
        super().__init__(message); self.message=message; self.code=code; self.status=status; self.details=details or []

def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
def list_items(filters):
    items = repository.all()
    for key in ("tipo_usuario", "estado"):
        if filters.get(key): items = [x for x in items if x[key] == filters[key]]
    return items
def get_item(item_id):
    item = repository.get(item_id)
    if not item: raise DomainError("Usuario no encontrado", "USER_NOT_FOUND", 404)
    return item
def create(data):
    model = UsuarioCreate.model_validate(data)
    if any(x["correo"] == model.correo for x in repository.all()): raise DomainError("El correo ya está registrado", "EMAIL_ALREADY_EXISTS", 409)
    return repository.add({"id": str(uuid4()), **model.model_dump(mode="json"), "estado":"ACTIVO", "fecha_creacion":now(), "fecha_ultimo_acceso":None})
def update(item_id, data):
    item=get_item(item_id); values=UsuarioUpdate.model_validate(data).model_dump(exclude_none=True, mode="json")
    if "correo" in values and any(x["correo"] == values["correo"] and x["id"] != item_id for x in repository.all()): raise DomainError("El correo ya está registrado", "EMAIL_ALREADY_EXISTS", 409)
    item.update(values); return item
def deactivate(item_id):
    item=get_item(item_id); item["estado"]="INACTIVO"; return item
