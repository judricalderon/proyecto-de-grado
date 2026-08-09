import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROGRESO = Path(__file__).resolve().parents[1] / "functions" / "progreso"


def response(row=None):
    if row is None:return {"columnMetadata":[],"records":[]}
    records=[]
    for value in row.values():
        if value is None:records.append({"isNull":True})
        elif isinstance(value,bool):records.append({"booleanValue":value})
        elif isinstance(value,int):records.append({"longValue":value})
        else:records.append({"stringValue":value})
    return {"columnMetadata":[{"name":key} for key in row],"records":[records]}


class ProgresoRepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.modules.pop("repository",None);sys.modules.pop("database",None);sys.path.insert(0,str(PROGRESO));cls.repository=importlib.import_module("repository")
    @classmethod
    def tearDownClass(cls):sys.path.remove(str(PROGRESO))

    def test_list_get_by_composite_and_id(self):
        row={"id":"id-1","id_propuesta":"PROP-1","id_fase":"FASE-1","estado":"NO_INICIADA","porcentaje_avance":0,"fecha_inicio":None,"fecha_ultima_actualizacion":"now","fecha_cierre":None}
        with patch.object(self.repository.database,"execute_statement",return_value=response(row)) as execute:
            self.assertEqual(self.repository.list_by_proposal("PROP-1"),[row])
            self.assertEqual(self.repository.get("PROP-1","FASE-1"),row)
            self.assertEqual(self.repository.get_by_id("id-1"),row)
            for item in execute.call_args_list:self.assertIsInstance(item.args[1],dict)

    def test_relations_create_update_and_parameterized_sql(self):
        row={"id":"id-1","id_propuesta":"PROP-1","id_fase":"FASE-1","estado":"EN_PROGRESO","porcentaje_avance":50,"fecha_inicio":"now","fecha_ultima_actualizacion":"now","fecha_cierre":None}
        with patch.object(self.repository.database,"execute_statement",side_effect=[response({"id":"PROP-1"}),response({"id":"FASE-1","activo":True})]):
            self.assertTrue(self.repository.proposal_exists("PROP-1"));self.assertTrue(self.repository.get_phase("FASE-1")["activo"])
        with patch.object(self.repository.database,"execute_write",return_value=[row]) as execute:
            self.assertEqual(self.repository.add(row),row)
            self.assertEqual(self.repository.update("PROP-1","FASE-1",{"estado":"EN_PROGRESO","porcentaje_avance":50,"fecha_ultima_actualizacion":"now"}),row)
            self.assertIn(":id_propuesta",execute.call_args.args[0]);self.assertEqual(execute.call_args.args[1]["porcentaje_avance"],50)
        with patch.object(self.repository.database,"execute_write",return_value=0):
            with self.assertRaises(self.repository.DuplicateProgressError):self.repository.add(row)

    def test_postgresql_errors_are_translated_and_sanitized(self):
        class Error(Exception):
            def __init__(self,code,message):self.response={"Error":{"DatabaseErrorCode":code,"Message":message}}
        cases=[("23505","duplicate key",self.repository.DuplicateProgressError),("23503","foreign key",self.repository.InvalidReferenceError),("23514","check constraint",self.repository.InvalidProgressStateError)]
        for code,message,expected in cases:
            with self.subTest(code=code),patch.object(self.repository.database,"execute_write",side_effect=Error(code,message)):
                with self.assertRaises(expected):self.repository.update("P","F",{"estado":"NO_INICIADA"})
        with patch.object(self.repository.database,"execute_statement",side_effect=RuntimeError("AWS secret detail")):
            with self.assertRaises(self.repository.RepositoryError) as caught:self.repository.list_by_proposal("P")
            self.assertNotIn("AWS secret detail",str(caught.exception))


if __name__=="__main__":unittest.main()
