import database


class RepositoryError(RuntimeError):
    pass


class ActiveOrderConflictError(RepositoryError):
    pass


class ActiveNameConflictError(RepositoryError):
    pass


_CONFIG = {
    "modulos": ("modulo", "id, nombre, descripcion, orden, activo"),
    "fases": ("fase", "id, id_modulo, nombre, descripcion, orden, activo"),
    "agentes": ("agente", "id, nombre, tipo_agente, descripcion, activo"),
}


def _config(kind):
    return _CONFIG[kind]


def _run(sql, parameters=None, write=False):
    try:
        function = database.execute_write if write else database.execute_statement
        return function(sql, parameters)
    except database.DatabaseConfigurationError:
        raise
    except (ActiveOrderConflictError, ActiveNameConflictError):
        raise
    except Exception as error:
        response = getattr(error, "response", {})
        detail = response.get("Error", {}) if isinstance(response, dict) else {}
        code = str(detail.get("DatabaseErrorCode", ""))
        message = str(detail.get("Message", "")).lower()
        if code == "23505" or "duplicate key" in message:
            if "uq_agente_nombre_activo" in message:
                raise ActiveNameConflictError("Nombre de agente duplicado") from error
            raise ActiveOrderConflictError("Orden activo duplicado") from error
        raise RepositoryError("No fue posible completar la operación de catálogos") from error


def reset():
    """Compatibilidad para el cargador de pruebas; no modifica PostgreSQL."""


def list_items(kind, module_id=None):
    table, columns = _config(kind)
    where = ""
    parameters = {}
    if kind == "fases" and module_id is not None:
        where = " WHERE id_modulo = :id_modulo"
        parameters["id_modulo"] = module_id
    response = _run(f"SELECT {columns} FROM {table}{where} ORDER BY id", parameters)
    return database.convert_records(response)


def get(kind, item_id):
    table, columns = _config(kind)
    response = _run(f"SELECT {columns} FROM {table} WHERE id = :id", {"id": item_id})
    records = database.convert_records(response)
    return records[0] if records else None


def add(kind, item):
    table, columns = _config(kind)
    names = [name.strip() for name in columns.split(",")]
    placeholders = ", ".join(f":{name}" for name in names)
    records = _run(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING {columns}",
        item,
        write=True,
    )
    return records[0]


def update(kind, item_id, values):
    table, columns = _config(kind)
    allowed = set(name.strip() for name in columns.split(",")) - {"id"}
    values = {key: value for key, value in values.items() if key in allowed}
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    records = _run(
        f"UPDATE {table} SET {assignments} WHERE id = :id RETURNING {columns}",
        {"id": item_id, **values},
        write=True,
    )
    return records[0] if records else None


def deactivate(kind, item_id):
    return update(kind, item_id, {"activo": False})


def active_order_exists(kind, order, module_id=None, exclude_id=None):
    table, _ = _config(kind)
    clauses = ["activo = true", "orden = :orden"]
    parameters = {"orden": order}
    if kind == "fases":
        clauses.append("id_modulo = :id_modulo")
        parameters["id_modulo"] = module_id
    if exclude_id:
        clauses.append("id <> :exclude_id")
        parameters["exclude_id"] = exclude_id
    response = _run(
        f"SELECT id FROM {table} WHERE {' AND '.join(clauses)} LIMIT 1",
        parameters,
    )
    return bool(response.get("records"))


def active_agent_name_exists(name, exclude_id=None):
    clauses = ["activo = true", "lower(nombre) = lower(:nombre)"]
    parameters = {"nombre": name}
    if exclude_id:
        clauses.append("id <> :exclude_id")
        parameters["exclude_id"] = exclude_id
    response = _run(
        f"SELECT id FROM agente WHERE {' AND '.join(clauses)} LIMIT 1",
        parameters,
    )
    return bool(response.get("records"))


def module_has_active_phases(module_id):
    response = _run(
        "SELECT id FROM fase WHERE id_modulo = :id_modulo AND activo = true LIMIT 1",
        {"id_modulo": module_id},
    )
    return bool(response.get("records"))
