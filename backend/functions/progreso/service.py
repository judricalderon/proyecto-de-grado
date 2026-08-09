from datetime import datetime, timezone
from uuid import uuid4

import repository as r
from models import ProgresoIn, ProgresoUpdate


class DomainError(Exception):
    def __init__(self, message, code, status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def refs(proposal_id, phase_id):
    if not r.proposal_exists(proposal_id):
        raise DomainError("Propuesta no encontrada", "PROPOSAL_NOT_FOUND", 404)
    phase = r.get_phase(phase_id)
    if not phase or not phase["activo"]:
        raise DomainError("Fase no encontrada", "PHASE_NOT_FOUND", 404)


def list_by_proposal(proposal_id):
    return r.list_by_proposal(proposal_id)


def create(proposal_id, data):
    model = ProgresoIn.model_validate(data)
    refs(proposal_id, model.id_fase)
    stamp = now()
    item = {
        "id": str(uuid4()),
        "id_propuesta": proposal_id,
        **model.model_dump(mode="json"),
        "fecha_inicio": stamp if model.estado.value != "NO_INICIADA" else None,
        "fecha_ultima_actualizacion": stamp,
        "fecha_cierre": stamp if model.estado.value == "COMPLETADA" else None,
    }
    try:
        return r.add(item)
    except r.DuplicateProgressError:
        raise DomainError("El progreso ya existe", "PROGRESS_ALREADY_EXISTS", 409)
    except r.InvalidReferenceError:
        refs(proposal_id, model.id_fase)
        raise DomainError("Referencia de progreso inválida", "VALIDATION_ERROR", 400)
    except r.InvalidProgressStateError:
        raise DomainError("El porcentaje no corresponde al estado", "VALIDATION_ERROR", 400)


def get(proposal_id, phase_id):
    refs(proposal_id, phase_id)
    item = r.get(proposal_id, phase_id)
    if not item:
        raise DomainError("Progreso no encontrado", "PROGRESS_NOT_FOUND", 404)
    return item


def update(proposal_id, phase_id, data):
    current = get(proposal_id, phase_id)
    model = ProgresoUpdate.model_validate(data)
    if current["estado"] == "COMPLETADA" and model.estado.value == "NO_INICIADA":
        raise DomainError("Use una acción explícita de reapertura", "REOPEN_REQUIRED", 409)
    stamp = now()
    values = {**model.model_dump(mode="json"), "fecha_ultima_actualizacion": stamp}
    if model.estado.value == "EN_PROGRESO" and not current["fecha_inicio"]:
        values["fecha_inicio"] = stamp
    if model.estado.value == "COMPLETADA":
        values["fecha_cierre"] = stamp
    try:
        item = r.update(proposal_id, phase_id, values)
    except r.InvalidProgressStateError:
        raise DomainError("El porcentaje no corresponde al estado", "VALIDATION_ERROR", 400)
    if not item:
        raise DomainError("Progreso no encontrado", "PROGRESS_NOT_FOUND", 404)
    return item
