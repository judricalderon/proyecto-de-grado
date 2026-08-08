from datetime import datetime, timezone
from uuid import uuid4

import repository as r
from models import DirectorCreate, EstudianteCreate, PropuestaCreate, PropuestaUpdate


class DomainError(Exception):
    def __init__(self, message, code, status=400, details=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.details = details or []


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def list_proposals():
    return r.all_proposals()


def proposal(proposal_id):
    item = r.get_proposal(proposal_id)
    if not item:
        raise DomainError("Propuesta no encontrada", "PROPOSAL_NOT_FOUND", 404)
    return item


def normalize(data):
    data = dict(data or {})
    if "titulo" in data:
        data.setdefault("titulo_tentativo", data["titulo"])
    if "descripcion" in data:
        data.setdefault("descripcion_inicial", data["descripcion"])
    return data


def create(data):
    model = PropuestaCreate.model_validate(normalize(data))
    stamp = now()
    return r.add_proposal(
        {
            "id": str(uuid4()),
            **model.model_dump(mode="json"),
            "estado_general": "BORRADOR",
            "fecha_creacion": stamp,
            "fecha_actualizacion": stamp,
        }
    )


def update(proposal_id, data):
    values = PropuestaUpdate.model_validate(normalize(data)).model_dump(exclude_none=True, mode="json")
    item = r.update_proposal(proposal_id, values, now())
    if not item:
        raise DomainError("Propuesta no encontrada", "PROPOSAL_NOT_FOUND", 404)
    return item


def close(proposal_id):
    item = r.close_proposal(proposal_id, now())
    if not item:
        raise DomainError("Propuesta no encontrada", "PROPOSAL_NOT_FOUND", 404)
    return item


def user(user_id, kind):
    item = r.get_user(user_id)
    if not item:
        raise DomainError("Usuario no encontrado", "USER_NOT_FOUND", 404)
    if item["estado"] != "ACTIVO":
        raise DomainError("El usuario está inactivo", "USER_INACTIVE", 409)
    if item["tipo_usuario"] != kind:
        raise DomainError("Tipo de usuario inválido", "INVALID_USER_TYPE", 409)
    return item


def students(proposal_id):
    proposal(proposal_id)
    return r.list_students(proposal_id)


def add_student(proposal_id, data):
    proposal(proposal_id)
    model = EstudianteCreate.model_validate(data)
    user(model.id_estudiante, "ESTUDIANTE")
    try:
        return r.add_student(
            {"id": str(uuid4()), "id_propuesta": proposal_id, "id_estudiante": model.id_estudiante}
        )
    except r.DuplicateStudentError:
        raise DomainError("El estudiante ya está asignado", "STUDENT_ALREADY_ASSIGNED", 409)


def remove_student(proposal_id, user_id):
    proposal(proposal_id)
    try:
        r.remove_student(proposal_id, user_id)
    except r.AssignmentNotFoundError:
        raise DomainError("Asignación no encontrada", "ASSIGNMENT_NOT_FOUND", 404)
    except r.LastStudentRequiredError:
        raise DomainError("No se puede retirar el último estudiante", "LAST_STUDENT_REQUIRED", 409)


def assign_director(proposal_id, data):
    proposal(proposal_id)
    model = DirectorCreate.model_validate(data)
    user(model.id_docente, "DOCENTE")
    relation = {
        "id": str(uuid4()),
        "id_propuesta": proposal_id,
        "id_docente": model.id_docente,
        "fecha_asignacion": now(),
        "estado": "ACTIVO",
    }
    try:
        return r.add_director(relation)
    except r.ActiveDirectorError:
        raise DomainError("La propuesta ya tiene director activo", "ACTIVE_DIRECTOR_EXISTS", 409)


def director(proposal_id):
    proposal(proposal_id)
    return r.get_active_director(proposal_id)


def unassign_director(proposal_id):
    proposal(proposal_id)
    item = r.deactivate_director(proposal_id)
    if not item:
        raise DomainError("Director activo no encontrado", "DIRECTOR_NOT_FOUND", 404)
    return item
