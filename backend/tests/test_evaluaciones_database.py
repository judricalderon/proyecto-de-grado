import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


EVALUACIONES = Path(__file__).resolve().parents[1] / "functions" / "evaluaciones"


def response(row=None):
    if row is None:
        return {"columnMetadata": [], "records": []}
    record = []
    for value in row.values():
        if value is None:
            record.append({"isNull": True})
        elif isinstance(value, bool):
            record.append({"booleanValue": value})
        elif isinstance(value, int):
            record.append({"longValue": value})
        else:
            record.append({"stringValue": value})
    return {"columnMetadata": [{"name": key} for key in row], "records": [record]}


class EvaluacionesRepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.modules.pop("repository", None)
        sys.modules.pop("database", None)
        sys.path.insert(0, str(EVALUACIONES))
        cls.repository = importlib.import_module("repository")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(EVALUACIONES))

    def setUp(self):
        self.row = {
            "id": "eval-1", "id_propuesta": "PROP-1", "id_fase": "FASE-1",
            "nivel_claridad": 1, "nivel_argumentacion": 5, "nivel_coherencia": 3,
            "fortalezas": "Claridad", "aspectos_por_fortalecer": "Fuentes",
            "observaciones": "", "fecha_evaluacion": "2026-01-01T00:00:00Z",
        }

    def test_list_by_proposal_and_phase_are_parameterized(self):
        with patch.object(self.repository.database, "execute_statement", return_value=response(self.row)) as execute:
            self.assertEqual(self.repository.list_by_proposal("PROP-1"), [self.row])
            sql, parameters = execute.call_args.args
            self.assertIn(":id_propuesta", sql); self.assertNotIn("PROP-1", sql)
            self.assertEqual(parameters, {"id_propuesta": "PROP-1"})
            self.assertEqual(self.repository.list_by_proposal("PROP-1", "FASE-1"), [self.row])
            sql, parameters = execute.call_args.args
            self.assertIn(":id_fase", sql); self.assertEqual(parameters["id_fase"], "FASE-1")

    def test_get_latest_order_and_relations(self):
        with patch.object(self.repository.database, "execute_statement", side_effect=[response(self.row), response(self.row), response({"id":"PROP-1"}), response({"id":"FASE-1","activo":True})]) as execute:
            self.assertEqual(self.repository.get("eval-1"), self.row)
            self.assertEqual(self.repository.latest("PROP-1", "FASE-1"), self.row)
            self.assertIn("ORDER BY fecha_evaluacion DESC LIMIT 1", execute.call_args_list[1].args[0])
            self.assertTrue(self.repository.proposal_exists("PROP-1"))
            self.assertTrue(self.repository.get_phase("FASE-1")["activo"])

    def test_create_uses_returning_and_all_parameters(self):
        with patch.object(self.repository.database, "execute_write", return_value=[self.row]) as execute:
            self.assertEqual(self.repository.add(self.row), self.row)
            sql, parameters = execute.call_args.args
            self.assertIn("INSERT INTO evaluacion_estado", sql); self.assertIn("RETURNING", sql)
            self.assertIn(":nivel_claridad", sql); self.assertEqual(parameters, self.row)

    def test_postgresql_errors_are_translated_and_unexpected_is_sanitized(self):
        class Error(Exception):
            def __init__(self, code, message):
                self.response = {"Error": {"DatabaseErrorCode": code, "Message": message}}
        cases = [("23503", "foreign key", self.repository.InvalidReferenceError), ("23514", "check constraint", self.repository.InvalidEvaluationLevelError)]
        for code, message, expected in cases:
            with self.subTest(code=code), patch.object(self.repository.database, "execute_write", side_effect=Error(code, message)):
                with self.assertRaises(expected): self.repository.add(self.row)
        with patch.object(self.repository.database, "execute_statement", side_effect=RuntimeError("AWS secret detail")):
            with self.assertRaises(self.repository.RepositoryError) as caught: self.repository.get("eval-1")
            self.assertNotIn("AWS secret detail", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
