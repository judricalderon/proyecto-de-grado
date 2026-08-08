import database


class RepositoryError(RuntimeError):
    pass


class DuplicateStudentError(RepositoryError):
    pass


class ActiveDirectorError(RepositoryError):
    pass


class AssignmentNotFoundError(RepositoryError):
    pass


class LastStudentRequiredError(RepositoryError):
    pass


_PROPOSAL_COLUMNS = "id, titulo_tentativo, descripcion_inicial, estado_general, fecha_creacion, fecha_actualizacion"
_STUDENT_COLUMNS = "id, id_propuesta, id_estudiante"
_DIRECTOR_COLUMNS = "id, id_propuesta, id_docente, fecha_asignacion, estado"
_USER_COLUMNS = "id, nombre, correo, tipo_usuario, estado, fecha_creacion, fecha_ultimo_acceso"


def _constraint(error):
    response = getattr(error, "response", {})
    detail = response.get("Error", {}) if isinstance(response, dict) else {}
    return str(detail.get("DatabaseErrorCode", "")), str(detail.get("Message", "")).lower()


def _run(sql, parameters=None, write=False, transaction_id=None):
    try:
        function = database.execute_write if write else database.execute_statement
        return function(sql, parameters, transaction_id)
    except database.DatabaseConfigurationError:
        raise
    except (DuplicateStudentError, ActiveDirectorError, AssignmentNotFoundError, LastStudentRequiredError):
        raise
    except Exception as error:
        code, message = _constraint(error)
        if code == "23505" or "duplicate key" in message:
            if "uq_propuesta_director_activo" in message:
                raise ActiveDirectorError("La propuesta ya tiene director activo") from error
            raise DuplicateStudentError("El estudiante ya está asignado") from error
        raise RepositoryError("No fue posible completar la operación de propuestas") from error


def reset():
    """Compatibilidad para el cargador de pruebas; no modifica PostgreSQL."""


def all_proposals():
    response = _run(f"SELECT {_PROPOSAL_COLUMNS} FROM propuesta_proyecto ORDER BY fecha_creacion, id")
    return database.convert_records(response)


def get_proposal(proposal_id):
    response = _run(f"SELECT {_PROPOSAL_COLUMNS} FROM propuesta_proyecto WHERE id = :id", {"id": proposal_id})
    records = database.convert_records(response)
    return records[0] if records else None


def add_proposal(proposal):
    records = _run(
        f"""INSERT INTO propuesta_proyecto ({_PROPOSAL_COLUMNS}) VALUES (
            :id, :titulo_tentativo, :descripcion_inicial, :estado_general,
            CAST(:fecha_creacion AS timestamptz), CAST(:fecha_actualizacion AS timestamptz)
        ) RETURNING {_PROPOSAL_COLUMNS}""",
        proposal,
        write=True,
    )
    return records[0]


def update_proposal(proposal_id, values, updated_at):
    allowed = {"titulo_tentativo", "descripcion_inicial", "estado_general"}
    values = {key: value for key, value in values.items() if key in allowed}
    assignments = [f"{key} = :{key}" for key in values]
    assignments.append("fecha_actualizacion = CAST(:fecha_actualizacion AS timestamptz)")
    records = _run(
        f"UPDATE propuesta_proyecto SET {', '.join(assignments)} WHERE id = :id RETURNING {_PROPOSAL_COLUMNS}",
        {"id": proposal_id, "fecha_actualizacion": updated_at, **values},
        write=True,
    )
    return records[0] if records else None


def close_proposal(proposal_id, updated_at):
    return update_proposal(proposal_id, {"estado_general": "CERRADA"}, updated_at)


def get_user(user_id):
    response = _run(f"SELECT {_USER_COLUMNS} FROM usuario WHERE id = :id", {"id": user_id})
    records = database.convert_records(response)
    return records[0] if records else None


def list_students(proposal_id):
    response = _run(
        """SELECT u.id, u.nombre, u.correo, u.tipo_usuario, u.estado,
                  u.fecha_creacion, u.fecha_ultimo_acceso
            FROM propuesta_estudiante pe
            JOIN usuario u ON u.id = pe.id_estudiante
            WHERE pe.id_propuesta = :id_propuesta
            ORDER BY u.nombre, u.id""",
        {"id_propuesta": proposal_id},
    )
    return database.convert_records(response)


def add_student(relation):
    records = _run(
        f"""INSERT INTO propuesta_estudiante ({_STUDENT_COLUMNS}) VALUES
            (:id, :id_propuesta, :id_estudiante)
            ON CONFLICT (id_propuesta, id_estudiante) DO NOTHING
            RETURNING {_STUDENT_COLUMNS}""",
        relation,
        write=True,
    )
    if not records:
        raise DuplicateStudentError("El estudiante ya está asignado")
    return records[0]


def remove_student(proposal_id, student_id):
    transaction_id = database.begin_transaction()
    try:
        proposal_response = _run(
            "SELECT estado_general FROM propuesta_proyecto WHERE id = :id FOR UPDATE",
            {"id": proposal_id},
            transaction_id=transaction_id,
        )
        proposals = database.convert_records(proposal_response)
        if not proposals:
            raise AssignmentNotFoundError("Propuesta no encontrada durante la asignación")
        relations_response = _run(
            f"SELECT {_STUDENT_COLUMNS} FROM propuesta_estudiante WHERE id_propuesta = :id_propuesta FOR UPDATE",
            {"id_propuesta": proposal_id},
            transaction_id=transaction_id,
        )
        relations = database.convert_records(relations_response)
        if not any(item["id_estudiante"] == student_id for item in relations):
            raise AssignmentNotFoundError("Asignación no encontrada")
        if len(relations) == 1 and proposals[0]["estado_general"] != "BORRADOR":
            raise LastStudentRequiredError("No se puede retirar el último estudiante")
        _run(
            "DELETE FROM propuesta_estudiante WHERE id_propuesta = :id_propuesta AND id_estudiante = :id_estudiante",
            {"id_propuesta": proposal_id, "id_estudiante": student_id},
            write=True,
            transaction_id=transaction_id,
        )
        database.commit_transaction(transaction_id)
    except Exception:
        try:
            database.rollback_transaction(transaction_id)
        except Exception:
            pass
        raise


def get_active_director(proposal_id):
    response = _run(
        """SELECT u.id, u.nombre, u.correo, u.tipo_usuario, u.estado,
                  u.fecha_creacion, u.fecha_ultimo_acceso
           FROM propuesta_director pd
           JOIN usuario u ON u.id = pd.id_docente
           WHERE pd.id_propuesta = :id_propuesta AND pd.estado = 'ACTIVO'""",
        {"id_propuesta": proposal_id},
    )
    records = database.convert_records(response)
    return records[0] if records else None


def add_director(relation):
    if get_active_director(relation["id_propuesta"]):
        raise ActiveDirectorError("La propuesta ya tiene director activo")
    records = _run(
        f"""INSERT INTO propuesta_director ({_DIRECTOR_COLUMNS}) VALUES
            (:id, :id_propuesta, :id_docente, CAST(:fecha_asignacion AS timestamptz), :estado)
            RETURNING {_DIRECTOR_COLUMNS}""",
        relation,
        write=True,
    )
    return records[0]


def deactivate_director(proposal_id):
    records = _run(
        f"""UPDATE propuesta_director SET estado = 'INACTIVO'
            WHERE id_propuesta = :id_propuesta AND estado = 'ACTIVO'
            RETURNING {_DIRECTOR_COLUMNS}""",
        {"id_propuesta": proposal_id},
        write=True,
    )
    return records[0] if records else None
