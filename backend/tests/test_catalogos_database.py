import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


CATALOGOS = Path(__file__).resolve().parents[1] / "functions" / "catalogos"


def response(row=None):
    if row is None:
        return {"columnMetadata": [], "records": []}
    return {
        "columnMetadata": [{"name": key} for key in row],
        "records": [[{"booleanValue": value} if isinstance(value, bool) else {"longValue": value} if isinstance(value, int) else {"stringValue": value} for value in row.values()]],
    }


class CatalogosRepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.modules.pop("repository", None);sys.modules.pop("database", None)
        sys.path.insert(0, str(CATALOGOS))
        cls.repository=importlib.import_module("repository")

    @classmethod
    def tearDownClass(cls):sys.path.remove(str(CATALOGOS))

    def test_list_get_create_update_and_deactivate(self):
        module={"id":"MOD-1","nombre":"M","descripcion":"D","orden":1,"activo":True}
        with patch.object(self.repository.database,"execute_statement",return_value=response(module)) as read, patch.object(self.repository.database,"execute_write",return_value=[module]) as write:
            self.assertEqual(self.repository.list_items("modulos"),[module])
            self.assertEqual(self.repository.get("modulos","MOD-1"),module)
            self.assertEqual(self.repository.add("modulos",module),module)
            self.assertEqual(self.repository.update("modulos","MOD-1",{"nombre":"Nuevo"}),module)
            self.assertEqual(self.repository.deactivate("modulos","MOD-1"),module)
            self.assertIn(":id",read.call_args.args[0]);self.assertIn(":activo",write.call_args.args[0])

    def test_phase_filter_and_business_checks_are_parameterized(self):
        with patch.object(self.repository.database,"execute_statement",side_effect=[response(),response({"id":"X"}),response({"id":"X"}),response({"id":"X"})]) as execute:
            self.assertEqual(self.repository.list_items("fases","MOD-1"),[])
            self.assertTrue(self.repository.active_order_exists("fases",1,"MOD-1","FASE-1"))
            self.assertTrue(self.repository.active_agent_name_exists("Orientador","AG-1"))
            self.assertTrue(self.repository.module_has_active_phases("MOD-1"))
            for item in execute.call_args_list:self.assertIsInstance(item.args[1],dict)

    def test_postgresql_conflicts_and_unexpected_errors_are_sanitized(self):
        class Error(Exception):
            def __init__(self,message):self.response={"Error":{"DatabaseErrorCode":"23505","Message":message}}
        with patch.object(self.repository.database,"execute_write",side_effect=Error("uq_modulo_orden_activo duplicate key")):
            with self.assertRaises(self.repository.ActiveOrderConflictError):self.repository.add("modulos",{})
        with patch.object(self.repository.database,"execute_write",side_effect=Error("uq_agente_nombre_activo duplicate key")):
            with self.assertRaises(self.repository.ActiveNameConflictError):self.repository.add("agentes",{})
        with patch.object(self.repository.database,"execute_statement",side_effect=RuntimeError("AWS secret detail")):
            with self.assertRaises(self.repository.RepositoryError) as caught:self.repository.list_items("modulos")
            self.assertNotIn("AWS secret detail",str(caught.exception))


if __name__=="__main__":unittest.main()
