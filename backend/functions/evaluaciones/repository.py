import database


class RepositoryError(RuntimeError):
    pass


class InvalidReferenceError(RepositoryError):
    pass


class InvalidEvaluationLevelError(RepositoryError):
    pass


_COLUMNS = "id, id_propuesta, id_fase, nivel_claridad, nivel_argumentacion, nivel_coherencia, fortalezas, aspectos_por_fortalecer, observaciones, fecha_evaluacion"


def _run(sql, parameters=None, write=False):
    try:
        function = database.execute_write if write else database.execute_statement
        return function(sql, parameters)
    except database.DatabaseConfigurationError:
        raise
    except (InvalidReferenceError, InvalidEvaluationLevelError):
        raise
    except Exception as error:
        response = getattr(error, "response", {})
        detail = response.get("Error", {}) if isinstance(response, dict) else {}
        code = str(detail.get("DatabaseErrorCode", ""))
        message = str(detail.get("Message", "")).lower()
        if code == "23503" or "foreign key" in message:
            raise InvalidReferenceError("Referencia de evaluación inválida") from error
        if code == "23514" or "check constraint" in message:
            raise InvalidEvaluationLevelError("Nivel de evaluación inválido") from error
        raise RepositoryError("No fue posible completar la operación de evaluación") from error


def reset():
    """Compatibilidad para el cargador de pruebas; no modifica PostgreSQL."""


def list_by_proposal(proposal_id, phase_id=None):
    parameters = {"id_propuesta": proposal_id}
    phase_filter = ""
    if phase_id is not None:
        phase_filter = " AND id_fase = :id_fase"
        parameters["id_fase"] = phase_id
    response = _run(
        f"SELECT {_COLUMNS} FROM evaluacion_estado WHERE id_propuesta = :id_propuesta{phase_filter} ORDER BY fecha_evaluacion, id",
        parameters,
    )
    return database.convert_records(response)


def get(item_id):
    response = _run(f"SELECT {_COLUMNS} FROM evaluacion_estado WHERE id = :id", {"id": item_id})
    records = database.convert_records(response)
    return records[0] if records else None


def latest(proposal_id, phase_id):
    response = _run(
        f"SELECT {_COLUMNS} FROM evaluacion_estado WHERE id_propuesta = :id_propuesta AND id_fase = :id_fase ORDER BY fecha_evaluacion DESC LIMIT 1",
        {"id_propuesta": proposal_id, "id_fase": phase_id},
    )
    records = database.convert_records(response)
    return records[0] if records else None


def proposal_exists(proposal_id):
    response = _run("SELECT id FROM propuesta_proyecto WHERE id = :id", {"id": proposal_id})
    return bool(response.get("records"))


def get_phase(phase_id):
    response = _run("SELECT id, activo FROM fase WHERE id = :id", {"id": phase_id})
    records = database.convert_records(response)
    return records[0] if records else None


def add(item):
    return _run(
        f"""INSERT INTO evaluacion_estado ({_COLUMNS}) VALUES (
            :id, :id_propuesta, :id_fase, :nivel_claridad, :nivel_argumentacion,
            :nivel_coherencia, :fortalezas, :aspectos_por_fortalecer, :observaciones,
            CAST(:fecha_evaluacion AS timestamptz)
        ) RETURNING {_COLUMNS}""",
        item,
        write=True,
    )[0]
