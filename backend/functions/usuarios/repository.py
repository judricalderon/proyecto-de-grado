import database


class RepositoryError(RuntimeError):
    pass


class DuplicateEmailError(RepositoryError):
    pass


_COLUMNS = "id, nombre, correo, tipo_usuario, estado, fecha_creacion, fecha_ultimo_acceso"


def _run(sql, parameters=None, write=False):
    try:
        return (database.execute_write if write else database.execute_statement)(sql, parameters)
    except database.DatabaseConfigurationError:
        raise
    except Exception as error:
        response = getattr(error, "response", {})
        detail = response.get("Error", {}) if isinstance(response, dict) else {}
        database_code = str(detail.get("DatabaseErrorCode", ""))
        message = str(detail.get("Message", "")).lower()
        if database_code == "23505" or "duplicate key" in message:
            raise DuplicateEmailError("El correo ya existe") from error
        raise RepositoryError("No fue posible completar la operación de usuarios") from error


def reset():
    """Compatibilidad para el cargador de tests; no modifica la base de datos."""


def all(filters=None):
    filters = filters or {}
    clauses = []
    parameters = {}
    if filters.get("correo"):
        clauses.append("lower(correo) = lower(:correo)")
        parameters["correo"] = filters["correo"]
    for key in ("tipo_usuario", "estado"):
        if filters.get(key):
            clauses.append(f"{key} = :{key}")
            parameters[key] = filters[key]
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    response = _run(f"SELECT {_COLUMNS} FROM usuario{where} ORDER BY fecha_creacion, id", parameters)
    return database.convert_records(response)


def get(item_id):
    response = _run(f"SELECT {_COLUMNS} FROM usuario WHERE id = :id", {"id": item_id})
    records = database.convert_records(response)
    return records[0] if records else None


def proposals_for_student(item_id):
    response = _run(
        """SELECT p.id, p.titulo_tentativo, p.descripcion_inicial, p.estado_general,
                  p.fecha_creacion, p.fecha_actualizacion
           FROM usuario u
           JOIN propuesta_estudiante pe ON pe.id_estudiante = u.id
           JOIN propuesta_proyecto p ON p.id = pe.id_propuesta
           WHERE u.id = :id AND u.tipo_usuario = 'ESTUDIANTE'
           ORDER BY p.fecha_creacion, p.id""",
        {"id": item_id},
    )
    return database.convert_records(response)


def add(item):
    sql = f"""
        INSERT INTO usuario ({_COLUMNS}) SELECT
            :id, :nombre, :correo, :tipo_usuario, :estado,
            CAST(:fecha_creacion AS timestamptz), CAST(:fecha_ultimo_acceso AS timestamptz)
        WHERE NOT EXISTS (SELECT 1 FROM usuario WHERE lower(correo) = lower(:correo))
        ON CONFLICT (correo) DO NOTHING
        RETURNING {_COLUMNS}
    """
    records = _run(sql, item, write=True)
    if not records:
        raise DuplicateEmailError("El correo ya existe")
    return records[0]


def update(item_id, values):
    allowed = {"nombre", "correo", "tipo_usuario", "estado"}
    values = {key: value for key, value in values.items() if key in allowed}
    if not values:
        return get(item_id)
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    params = {"id": item_id, **values}
    email_guard = ""
    if "correo" in values:
        email_guard = " AND NOT EXISTS (SELECT 1 FROM usuario other WHERE lower(other.correo) = lower(:correo) AND other.id <> :id)"
    records = _run(f"UPDATE usuario SET {assignments} WHERE id = :id{email_guard} RETURNING {_COLUMNS}", params, write=True)
    if records:
        return records[0]
    if get(item_id) is None:
        return None
    if "correo" in values:
        raise DuplicateEmailError("El correo ya existe")
    return None


def deactivate(item_id):
    records = _run(
        f"UPDATE usuario SET estado = 'INACTIVO' WHERE id = :id RETURNING {_COLUMNS}",
        {"id": item_id},
        write=True,
    )
    return records[0] if records else None
