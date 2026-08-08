import os
from datetime import date, datetime
from decimal import Decimal

import boto3


class DatabaseConfigurationError(RuntimeError):
    pass


def _configuration():
    names = ("DB_CLUSTER_ARN", "DB_SECRET_ARN", "DB_NAME")
    values = {name: os.environ.get(name) for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise DatabaseConfigurationError(
            "Faltan variables de configuración de base de datos: " + ", ".join(missing)
        )
    return values


def _parameter(name, value):
    parameter = {"name": name}
    if value is None:
        parameter["value"] = {"isNull": True}
    elif isinstance(value, bool):
        parameter["value"] = {"booleanValue": value}
    elif isinstance(value, int):
        parameter["value"] = {"longValue": value}
    elif isinstance(value, (float, Decimal)):
        parameter["value"] = {"doubleValue": float(value)}
    elif isinstance(value, (datetime, date)):
        parameter["value"] = {"stringValue": value.isoformat()}
        parameter["typeHint"] = "TIMESTAMP" if isinstance(value, datetime) else "DATE"
    else:
        parameter["value"] = {"stringValue": str(value)}
    return parameter


def _value(field):
    if not field or field.get("isNull"):
        return None
    for key in ("stringValue", "longValue", "doubleValue", "booleanValue"):
        if key in field:
            return field[key]
    if "blobValue" in field:
        return field["blobValue"]
    if "arrayValue" in field:
        array = field["arrayValue"]
        for key in ("stringValues", "longValues", "doubleValues", "booleanValues"):
            if key in array:
                return array[key]
    raise ValueError("Formato de valor desconocido en respuesta de Data API")


def convert_records(response):
    columns = [column["name"] for column in response.get("columnMetadata", [])]
    return [
        {name: _value(value) for name, value in zip(columns, record)}
        for record in response.get("records", [])
    ]


def _request():
    config = _configuration()
    return {
        "resourceArn": config["DB_CLUSTER_ARN"],
        "secretArn": config["DB_SECRET_ARN"],
        "database": config["DB_NAME"],
    }


def execute_statement(sql, parameters=None, transaction_id=None):
    request = {
        **_request(),
        "sql": sql,
        "parameters": [_parameter(name, value) for name, value in (parameters or {}).items()],
        "includeResultMetadata": True,
    }
    if transaction_id:
        request["transactionId"] = transaction_id
    return boto3.client("rds-data").execute_statement(**request)


def execute_write(sql, parameters=None, transaction_id=None):
    response = execute_statement(sql, parameters, transaction_id)
    return convert_records(response) if response.get("records") else response.get("numberOfRecordsUpdated", 0)


def begin_transaction():
    return boto3.client("rds-data").begin_transaction(**_request())["transactionId"]


def commit_transaction(transaction_id):
    request = _request()
    request.pop("database")
    return boto3.client("rds-data").commit_transaction(**request, transactionId=transaction_id)


def rollback_transaction(transaction_id):
    request = _request()
    request.pop("database")
    return boto3.client("rds-data").rollback_transaction(**request, transactionId=transaction_id)
