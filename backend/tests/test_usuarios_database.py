import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


USUARIOS = Path(__file__).resolve().parents[1] / "functions" / "usuarios"


class UsuariosDatabaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.modules.pop("repository", None)
        sys.modules.pop("database", None)
        sys.path.insert(0, str(USUARIOS))
        cls.database = importlib.import_module("database")
        cls.repository = importlib.import_module("repository")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(USUARIOS))

    def test_convert_records_all_supported_scalar_types(self):
        response = {
            "columnMetadata": [{"name": x} for x in ("texto", "entero", "decimal", "activo", "vacio")],
            "records": [[
                {"stringValue": "uno"}, {"longValue": 2}, {"doubleValue": 3.5},
                {"booleanValue": True}, {"isNull": True},
            ]],
        }
        self.assertEqual(
            self.database.convert_records(response),
            [{"texto":"uno","entero":2,"decimal":3.5,"activo":True,"vacio":None}],
        )

    @patch.dict(os.environ, {"DB_CLUSTER_ARN":"cluster","DB_SECRET_ARN":"secret","DB_NAME":"db"})
    @patch("database.boto3.client")
    def test_execute_statement_uses_data_api_and_parameters(self, client):
        rds = client.return_value
        rds.execute_statement.return_value = {"records": []}
        self.database.execute_statement("SELECT :id", {"id":"USR-001", "activo":True})
        client.assert_called_once_with("rds-data")
        request = rds.execute_statement.call_args.kwargs
        self.assertEqual(request["resourceArn"], "cluster")
        self.assertEqual(request["parameters"][0]["value"], {"stringValue":"USR-001"})
        self.assertNotIn("SELECT :id", str(request["parameters"]))

    def test_list_get_create_update_deactivate_and_not_found(self):
        row = {"id":"id-1","nombre":"Ana","correo":"ana@example.com","tipo_usuario":"ESTUDIANTE","estado":"ACTIVO","fecha_creacion":"2026-01-01T00:00:00Z","fecha_ultimo_acceso":None}
        response = {"columnMetadata":[{"name":k} for k in row], "records":[[
            {"isNull":True} if value is None else {"stringValue":value} for value in row.values()
        ]]}
        with patch.object(self.repository.database, "execute_statement", return_value=response), patch.object(self.repository.database, "execute_write", return_value=[row]) as write:
            self.assertEqual(self.repository.all(), [row])
            self.assertEqual(self.repository.get("id-1"), row)
            self.assertEqual(self.repository.add(row), row)
            self.assertEqual(self.repository.update("id-1", {"nombre":"Ana María"})["id"], "id-1")
            self.assertEqual(self.repository.deactivate("id-1")["estado"], "ACTIVO")
            self.assertIn(":id", write.call_args_list[-1].args[0])
        empty = {"columnMetadata":[], "records":[]}
        with patch.object(self.repository.database, "execute_statement", return_value=empty):
            self.assertIsNone(self.repository.get("missing"))

    def test_duplicate_email_and_unexpected_data_api_error(self):
        with patch.object(self.repository.database, "execute_write", return_value=0):
            with self.assertRaises(self.repository.DuplicateEmailError):
                self.repository.add({})
        with patch.object(self.repository.database, "execute_statement", side_effect=RuntimeError("AWS detail")):
            with self.assertRaisesRegex(self.repository.RepositoryError, "operación de usuarios") as caught:
                self.repository.all()
            self.assertNotIn("AWS detail", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
