import database


class RepositoryError(RuntimeError):
    pass


class InvalidReferenceError(RepositoryError):
    pass


class InvalidDocumentTypeError(RepositoryError):
    pass


_COLUMNS = "id, id_propuesta, tipo_documento, nombre_archivo, ruta, fecha_carga"


def _run(sql, parameters=None, write=False):
    try:
        function = database.execute_write if write else database.execute_statement
        return function(sql, parameters)
    except database.DatabaseConfigurationError:
        raise
    except (InvalidReferenceError, InvalidDocumentTypeError):
        raise
    except Exception as error:
        response = getattr(error, "response", {})
        detail = response.get("Error", {}) if isinstance(response, dict) else {}
        code = str(detail.get("DatabaseErrorCode", ""))
        message = str(detail.get("Message", "")).lower()
        if code == "23503" or "foreign key" in message:
            raise InvalidReferenceError("Referencia de propuesta inválida") from error
        if code == "23514" or "check constraint" in message:
            raise InvalidDocumentTypeError("Tipo de documento inválido") from error
        raise RepositoryError("No fue posible completar la operación de documento") from error


def reset():
    """Compatibilidad para el cargador de pruebas; no modifica PostgreSQL."""


def list_by_proposal(proposal_id):
    response = _run(
        f"SELECT {_COLUMNS} FROM documento_soporte WHERE id_propuesta = :id_propuesta ORDER BY fecha_carga, id",
        {"id_propuesta": proposal_id},
    )
    return database.convert_records(response)


def get(item_id):
    response = _run(f"SELECT {_COLUMNS} FROM documento_soporte WHERE id = :id", {"id": item_id})
    records = database.convert_records(response)
    return records[0] if records else None


def proposal_exists(proposal_id):
    response = _run("SELECT id FROM propuesta_proyecto WHERE id = :id", {"id": proposal_id})
    return bool(response.get("records"))


def add(item):
    return _run(
        f"""INSERT INTO documento_soporte ({_COLUMNS}) VALUES (
            :id, :id_propuesta, :tipo_documento, :nombre_archivo, :ruta,
            CAST(:fecha_carga AS timestamptz)
        ) RETURNING {_COLUMNS}""",
        item,
        write=True,
    )[0]


def update(item_id, values):
    allowed = {"tipo_documento", "nombre_archivo", "ruta"}
    values = {key: value for key, value in values.items() if key in allowed}
    assignments = [f"{key} = :{key}" for key in values]
    records = _run(
        f"UPDATE documento_soporte SET {', '.join(assignments)} WHERE id = :id RETURNING {_COLUMNS}",
        {"id": item_id, **values},
        write=True,
    )
    return records[0] if records else None


def delete(item_id):
    records = _run(
        f"DELETE FROM documento_soporte WHERE id = :id RETURNING {_COLUMNS}",
        {"id": item_id},
        write=True,
    )
    return records[0] if records else None
