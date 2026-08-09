from datetime import datetime, timezone
from uuid import uuid4

import repository as r
from models import DocumentoIn, DocumentoUpdate


class DomainError(Exception):
    def __init__(self, message, code, status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def list_by_proposal(proposal_id):
    return r.list_by_proposal(proposal_id)


def create(proposal_id, data):
    if not r.proposal_exists(proposal_id):
        raise DomainError("Propuesta no encontrada", "PROPOSAL_NOT_FOUND", 404)
    model = DocumentoIn.model_validate(data)
    item = {
        "id": str(uuid4()),
        "id_propuesta": proposal_id,
        **model.model_dump(mode="json"),
        "fecha_carga": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    try:
        return r.add(item)
    except r.InvalidReferenceError:
        if not r.proposal_exists(proposal_id):
            raise DomainError("Propuesta no encontrada", "PROPOSAL_NOT_FOUND", 404)
        raise DomainError("Referencia de propuesta inválida", "VALIDATION_ERROR", 400)
    except r.InvalidDocumentTypeError:
        raise DomainError("Tipo de documento inválido", "VALIDATION_ERROR", 400)


def get(item_id):
    item = r.get(item_id)
    if not item:
        raise DomainError("Documento no encontrado", "DOCUMENT_NOT_FOUND", 404)
    return item


def update(item_id, data):
    current = get(item_id)
    values = DocumentoUpdate.model_validate(data).model_dump(exclude_none=True, mode="json")
    if not values:
        return current
    try:
        item = r.update(item_id, values)
    except r.InvalidDocumentTypeError:
        raise DomainError("Tipo de documento inválido", "VALIDATION_ERROR", 400)
    if not item:
        raise DomainError("Documento no encontrado", "DOCUMENT_NOT_FOUND", 404)
    return item


def delete(item_id):
    if not r.delete(item_id):
        raise DomainError("Documento no encontrado", "DOCUMENT_NOT_FOUND", 404)
