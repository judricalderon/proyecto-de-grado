from datetime import datetime, timezone
from uuid import uuid4

import repository
from models import UsuarioCreate, UsuarioUpdate


class DomainError(Exception):
    def __init__(self, message, code, status=400, details=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.details = details or []


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def list_items(filters):
    items = repository.all()
    for key in ("tipo_usuario", "estado"):
        if filters.get(key):
            items = [item for item in items if item[key] == filters[key]]
    return items


def get_item(item_id):
    item = repository.get(item_id)
    if not item:
        raise DomainError("Usuario no encontrado", "USER_NOT_FOUND", 404)
    return item


def create(data):
    model = UsuarioCreate.model_validate(data)
    try:
        return repository.add(
            {
                "id": str(uuid4()),
                **model.model_dump(mode="json"),
                "estado": "ACTIVO",
                "fecha_creacion": now(),
                "fecha_ultimo_acceso": None,
            }
        )
    except repository.DuplicateEmailError:
        raise DomainError("El correo ya está registrado", "EMAIL_ALREADY_EXISTS", 409)


def update(item_id, data):
    values = UsuarioUpdate.model_validate(data).model_dump(exclude_none=True, mode="json")
    try:
        item = repository.update(item_id, values)
    except repository.DuplicateEmailError:
        raise DomainError("El correo ya está registrado", "EMAIL_ALREADY_EXISTS", 409)
    if not item:
        raise DomainError("Usuario no encontrado", "USER_NOT_FOUND", 404)
    return item


def deactivate(item_id):
    item = repository.deactivate(item_id)
    if not item:
        raise DomainError("Usuario no encontrado", "USER_NOT_FOUND", 404)
    return item
