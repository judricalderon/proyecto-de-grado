from uuid import uuid4

import repository as r
from models import AgenteIn, FaseIn, ModuloIn


class DomainError(Exception):
    def __init__(self, message, code, status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def cfg(kind):
    return {
        "modulos": (ModuloIn, "MOD"),
        "fases": (FaseIn, "FASE"),
        "agentes": (AgenteIn, "AG"),
    }[kind]


def list_items(kind, module_id=None):
    return r.list_items(kind, module_id)


def get(kind, item_id):
    item = r.get(kind, item_id)
    if not item:
        raise DomainError("Recurso no encontrado", "RESOURCE_NOT_FOUND", 404)
    return item


def validate(kind, data, current_id=None):
    model, _ = cfg(kind)
    values = model.model_validate(data).model_dump(mode="json")
    if kind == "modulos" and r.active_order_exists(kind, values["orden"], exclude_id=current_id):
        raise DomainError("Orden duplicado", "ACTIVE_ORDER_CONFLICT", 409)
    if kind == "fases":
        module = r.get("modulos", values["id_modulo"])
        if not module or not module["activo"]:
            raise DomainError("Módulo inexistente o inactivo", "MODULE_NOT_ACTIVE", 409)
        if r.active_order_exists(
            kind, values["orden"], module_id=values["id_modulo"], exclude_id=current_id
        ):
            raise DomainError("Orden duplicado en el módulo", "ACTIVE_ORDER_CONFLICT", 409)
    if kind == "agentes" and r.active_agent_name_exists(values["nombre"], exclude_id=current_id):
        raise DomainError("Nombre de agente duplicado", "ACTIVE_NAME_CONFLICT", 409)
    return values


def _translate_conflict(kind, operation):
    try:
        return operation()
    except r.ActiveOrderConflictError:
        message = "Orden duplicado en el módulo" if kind == "fases" else "Orden duplicado"
        raise DomainError(message, "ACTIVE_ORDER_CONFLICT", 409)
    except r.ActiveNameConflictError:
        raise DomainError("Nombre de agente duplicado", "ACTIVE_NAME_CONFLICT", 409)


def create(kind, data):
    _, prefix = cfg(kind)
    item = {"id": f"{prefix}-{uuid4()}", **validate(kind, data)}
    return _translate_conflict(kind, lambda: r.add(kind, item))


def update(kind, item_id, data):
    current = get(kind, item_id)
    merged = {**current, **data}
    merged.pop("id", None)
    values = validate(kind, merged, item_id)
    item = _translate_conflict(kind, lambda: r.update(kind, item_id, values))
    if not item:
        raise DomainError("Recurso no encontrado", "RESOURCE_NOT_FOUND", 404)
    return item


def deactivate(kind, item_id):
    get(kind, item_id)
    if kind == "modulos" and r.module_has_active_phases(item_id):
        raise DomainError("El módulo tiene fases activas", "MODULE_HAS_ACTIVE_PHASES", 409)
    item = r.deactivate(kind, item_id)
    if not item:
        raise DomainError("Recurso no encontrado", "RESOURCE_NOT_FOUND", 404)
    return item
