import json

from pydantic import ValidationError

import repository as r
import service


def out(status_code, response_body=None):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": (
            ""
            if response_body is None
            else json.dumps(response_body, ensure_ascii=False)
        ),
    }


def body(event):
    try:
        raw_body = event.get("body")

        if isinstance(raw_body, str):
            return json.loads(raw_body)

        return raw_body

    except Exception:
        raise service.DomainError(
            "JSON inválido",
            "VALIDATION_ERROR",
        )


def lambda_handler(event, context):
    try:
        request_context = event.get("requestContext", {})
        http_context = request_context.get("http", {})

        method = http_context.get("method", "")
        path = event.get("rawPath", "")
        stage = request_context.get("stage", "")

        # API Gateway puede incluir el stage dentro de rawPath.
        # Ejemplo:
        # /dev/documentos/health
        #
        # Después de normalizar:
        # /documentos/health
        stage_prefix = f"/{stage}"

        if stage and path.startswith(stage_prefix + "/"):
            path = path[len(stage_prefix):]

        print(
            {
                "normalizedPath": path,
                "stage": stage,
                "routeKey": event.get("routeKey"),
                "method": method,
            }
        )

        path_parameters = event.get("pathParameters") or {}

        proposal_id = path_parameters.get("id_propuesta")
        document_id = path_parameters.get("id")

        # GET /documentos/health
        if method == "GET" and path == "/documentos/health":
            return out(
                200,
                {
                    "data": {
                        "service": "documentos",
                        "status": "ok",
                    }
                },
            )

        # GET /propuestas/{id_propuesta}/documentos
        if method == "GET" and path.endswith("/documentos"):
            documents = [
                item
                for item in r.items
                if item["id_propuesta"] == proposal_id
            ]

            return out(
                200,
                {
                    "data": documents,
                    "count": len(documents),
                },
            )

        # POST /propuestas/{id_propuesta}/documentos
        if method == "POST" and path.endswith("/documentos"):
            created_document = service.create(
                proposal_id,
                body(event),
            )

            return out(
                201,
                {
                    "message": "Documento creado correctamente",
                    "data": created_document,
                },
            )

        # GET /documentos/{id}
        if method == "GET" and path.startswith("/documentos/"):
            return out(
                200,
                {
                    "data": service.get(document_id),
                },
            )

        # PUT /documentos/{id}
        if method == "PUT" and path.startswith("/documentos/"):
            updated_document = service.update(
                document_id,
                body(event),
            )

            return out(
                200,
                {
                    "message": "Documento actualizado correctamente",
                    "data": updated_document,
                },
            )

        # DELETE /documentos/{id}
        if method == "DELETE" and path.startswith("/documentos/"):
            service.delete(document_id)

            return out(204)

        return out(
            404,
            {
                "error": "Ruta no encontrada",
                "code": "ROUTE_NOT_FOUND",
                "details": [],
            },
        )

    except ValidationError as error:
        return out(
            400,
            {
                "error": "Datos de entrada inválidos",
                "code": "VALIDATION_ERROR",
                "details": [
                    validation_error["msg"]
                    for validation_error in error.errors()
                ],
            },
        )

    except service.DomainError as error:
        return out(
            error.status,
            {
                "error": error.message,
                "code": error.code,
                "details": [],
            },
        )

    except Exception as error:
        print(
            {
                "error": str(error),
                "type": type(error).__name__,
            }
        )

        return out(
            500,
            {
                "error": "Error interno del servidor",
                "code": "INTERNAL_SERVER_ERROR",
                "details": [],
            },
        )