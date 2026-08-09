import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from botocore.exceptions import ClientError


FUNCTIONS = Path(__file__).resolve().parents[1] / "functions"


def load_database(domain):
    path = FUNCTIONS / domain / "database.py"
    spec = importlib.util.spec_from_file_location(f"{domain}_retry_database", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def client_error(code):
    return ClientError({"Error": {"Code": code, "Message": code}}, "ExecuteStatement")


class DatabaseRetryContract:
    domain = None

    @classmethod
    def setUpClass(cls):
        cls.database = load_database(cls.domain)

    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {"DB_CLUSTER_ARN": "cluster", "DB_SECRET_ARN": "secret", "DB_NAME": "database"},
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def execute_with(self, side_effect, parameters=None, transaction_id=None):
        rds = MagicMock()
        rds.execute_statement.side_effect = side_effect
        with patch.object(self.database.boto3, "client", return_value=rds), patch.object(
            self.database.time, "sleep"
        ) as sleep:
            result = self.database.execute_statement(
                "SELECT :id", parameters or {"id": "value"}, transaction_id
            )
        return result, rds, sleep

    def test_first_resuming_exception_then_success(self):
        expected = {"records": []}
        result, rds, sleep = self.execute_with(
            [client_error("DatabaseResumingException"), expected]
        )
        self.assertEqual(result, expected)
        self.assertEqual(rds.execute_statement.call_count, 2)
        sleep.assert_called_once_with(0.5)

    def test_multiple_resuming_exceptions_then_success(self):
        expected = {"records": []}
        result, rds, sleep = self.execute_with(
            [
                client_error("DatabaseResumingException"),
                client_error("DatabaseResumingException"),
                expected,
            ]
        )
        self.assertEqual(result, expected)
        self.assertEqual(rds.execute_statement.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(0.5), call(1.0)])

    def test_maximum_attempts_reraises(self):
        rds = MagicMock()
        error = client_error("DatabaseResumingException")
        rds.execute_statement.side_effect = error
        with patch.object(self.database.boto3, "client", return_value=rds), patch.object(
            self.database.time, "sleep"
        ) as sleep:
            with self.assertRaises(ClientError) as caught:
                self.database.execute_statement("SELECT 1")
        self.assertIs(caught.exception, error)
        self.assertEqual(rds.execute_statement.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(0.5), call(1.0)])

    def test_different_exception_is_not_retried(self):
        rds = MagicMock()
        error = client_error("AccessDeniedException")
        rds.execute_statement.side_effect = error
        with patch.object(self.database.boto3, "client", return_value=rds), patch.object(
            self.database.time, "sleep"
        ) as sleep:
            with self.assertRaises(ClientError) as caught:
                self.database.execute_statement("SELECT 1")
        self.assertIs(caught.exception, error)
        rds.execute_statement.assert_called_once()
        sleep.assert_not_called()

    def test_parameters_and_transaction_id_are_preserved(self):
        expected = {"records": []}
        parameters = {"id": "PROP-001", "active": True}
        _, rds, _ = self.execute_with(
            [client_error("DatabaseResumingException"), expected], parameters, "tx-123"
        )
        first, second = rds.execute_statement.call_args_list
        self.assertEqual(first.kwargs, second.kwargs)
        self.assertEqual(second.kwargs["transactionId"], "tx-123")
        self.assertEqual(
            second.kwargs["parameters"],
            [
                {"name": "id", "value": {"stringValue": "PROP-001"}},
                {"name": "active", "value": {"booleanValue": True}},
            ],
        )


class UsuariosDatabaseRetryTest(DatabaseRetryContract, unittest.TestCase):
    domain = "usuarios"


class PropuestasDatabaseRetryTest(DatabaseRetryContract, unittest.TestCase):
    domain = "propuestas"


class CatalogosDatabaseRetryTest(DatabaseRetryContract, unittest.TestCase):
    domain = "catalogos"


class ProgresoDatabaseRetryTest(DatabaseRetryContract, unittest.TestCase):
    domain = "progreso"


class EvaluacionesDatabaseRetryTest(DatabaseRetryContract, unittest.TestCase):
    domain = "evaluaciones"


class DocumentosDatabaseRetryTest(DatabaseRetryContract, unittest.TestCase):
    domain = "documentos"


if __name__ == "__main__":
    unittest.main()
