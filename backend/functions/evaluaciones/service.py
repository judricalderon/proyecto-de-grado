from datetime import datetime, timezone
from uuid import uuid4

import repository as r
from models import EvaluacionIn


class DomainError(Exception):
    def __init__(self, message, code, status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def refs(proposal_id, phase_id=None):
    if not r.proposal_exists(proposal_id):
        raise DomainError("Propuesta no encontrada", "PROPOSAL_NOT_FOUND", 404)
    if phase_id:
        phase = r.get_phase(phase_id)
        if not phase or not phase["activo"]:
            raise DomainError("Fase no encontrada", "PHASE_NOT_FOUND", 404)


def list_by_proposal(proposal_id, phase_id=None):
    refs(proposal_id, phase_id)
    return r.list_by_proposal(proposal_id, phase_id)


def create(proposal_id, phase_id, data):
    refs(proposal_id, phase_id)
    model = EvaluacionIn.model_validate(data)
    item = {
        "id": str(uuid4()),
        "id_propuesta": proposal_id,
        "id_fase": phase_id,
        **model.model_dump(),
        "fecha_evaluacion": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    try:
        return r.add(item)
    except r.InvalidReferenceError:
        refs(proposal_id, phase_id)
        raise DomainError("Referencia de evaluación inválida", "VALIDATION_ERROR", 400)
    except r.InvalidEvaluationLevelError:
        raise DomainError("Nivel de evaluación inválido", "VALIDATION_ERROR", 400)


def get(item_id):
    item = r.get(item_id)
    if not item:
        raise DomainError("Evaluación no encontrada", "EVALUATION_NOT_FOUND", 404)
    return item


def latest(proposal_id, phase_id):
    refs(proposal_id, phase_id)
    item = r.latest(proposal_id, phase_id)
    if not item:
        raise DomainError("Evaluación no encontrada", "EVALUATION_NOT_FOUND", 404)
    return item
