import database


class RepositoryError(RuntimeError):
    pass


class DuplicateProgressError(RepositoryError):
    pass


class InvalidReferenceError(RepositoryError):
    pass


class InvalidProgressStateError(RepositoryError):
    pass


_COLUMNS = "id, id_propuesta, id_fase, estado, porcentaje_avance, fecha_inicio, fecha_ultima_actualizacion, fecha_cierre"


def _run(sql, parameters=None, write=False):
    try:
        function = database.execute_write if write else database.execute_statement
        return function(sql, parameters)
    except database.DatabaseConfigurationError:
        raise
    except (DuplicateProgressError, InvalidReferenceError, InvalidProgressStateError):
        raise
    except Exception as error:
        response = getattr(error, "response", {})
        detail = response.get("Error", {}) if isinstance(response, dict) else {}
        code = str(detail.get("DatabaseErrorCode", ""))
        message = str(detail.get("Message", "")).lower()
        if code == "23505" or "duplicate key" in message:
            raise DuplicateProgressError("El progreso ya existe") from error
        if code == "23503" or "foreign key" in message:
            raise InvalidReferenceError("Referencia de progreso inválida") from error
        if code == "23514" or "check constraint" in message:
            raise InvalidProgressStateError("Estado y porcentaje incompatibles") from error
        raise RepositoryError("No fue posible completar la operación de progreso") from error


def reset():
    """Compatibilidad para el cargador de pruebas; no modifica PostgreSQL."""


def list_by_proposal(proposal_id):
    response = _run(
        f"SELECT {_COLUMNS} FROM progreso_fase WHERE id_propuesta = :id_propuesta ORDER BY id_fase, id",
        {"id_propuesta": proposal_id},
    )
    return database.convert_records(response)


def get(proposal_id, phase_id):
    response = _run(
        f"SELECT {_COLUMNS} FROM progreso_fase WHERE id_propuesta = :id_propuesta AND id_fase = :id_fase",
        {"id_propuesta": proposal_id, "id_fase": phase_id},
    )
    records = database.convert_records(response)
    return records[0] if records else None


def get_by_id(item_id):
    response = _run(f"SELECT {_COLUMNS} FROM progreso_fase WHERE id = :id", {"id": item_id})
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
    records = _run(
        f"""INSERT INTO progreso_fase ({_COLUMNS}) VALUES (
            :id, :id_propuesta, :id_fase, :estado, :porcentaje_avance,
            CAST(:fecha_inicio AS timestamptz), CAST(:fecha_ultima_actualizacion AS timestamptz),
            CAST(:fecha_cierre AS timestamptz)
        ) ON CONFLICT (id_propuesta, id_fase) DO NOTHING RETURNING {_COLUMNS}""",
        item,
        write=True,
    )
    if not records:
        raise DuplicateProgressError("El progreso ya existe")
    return records[0]


def update(proposal_id, phase_id, values):
    allowed = {"estado", "porcentaje_avance", "fecha_inicio", "fecha_ultima_actualizacion", "fecha_cierre"}
    values = {key: value for key, value in values.items() if key in allowed}
    assignments = []
    for key in values:
        expression = f"CAST(:{key} AS timestamptz)" if key.startswith("fecha_") else f":{key}"
        assignments.append(f"{key} = {expression}")
    records = _run(
        f"UPDATE progreso_fase SET {', '.join(assignments)} WHERE id_propuesta = :id_propuesta AND id_fase = :id_fase RETURNING {_COLUMNS}",
        {"id_propuesta": proposal_id, "id_fase": phase_id, **values},
        write=True,
    )
    return records[0] if records else None
