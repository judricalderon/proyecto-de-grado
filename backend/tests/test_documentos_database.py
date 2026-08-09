import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


DOCUMENTOS = Path(__file__).resolve().parents[1] / "functions" / "documentos"


def response(row=None):
    if row is None:return {"columnMetadata":[],"records":[]}
    record=[]
    for value in row.values():
        if value is None:record.append({"isNull":True})
        elif isinstance(value,bool):record.append({"booleanValue":value})
        elif isinstance(value,int):record.append({"longValue":value})
        else:record.append({"stringValue":value})
    return {"columnMetadata":[{"name":key} for key in row],"records":[record]}


class DocumentosRepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.modules.pop("repository",None);sys.modules.pop("database",None)
        sys.path.insert(0,str(DOCUMENTOS));cls.repository=importlib.import_module("repository")
    @classmethod
    def tearDownClass(cls):sys.path.remove(str(DOCUMENTOS))
    def setUp(self):
        self.row={"id":"doc-1","id_propuesta":"PROP-1","tipo_documento":"ANEXO","nombre_archivo":"a.pdf","ruta":"temporal/a.pdf","fecha_carga":"2026-01-01T00:00:00Z"}

    def test_list_empty_get_and_parameterized_sql(self):
        with patch.object(self.repository.database,"execute_statement",side_effect=[response(self.row),response(),response(self.row)]) as execute:
            self.assertEqual(self.repository.list_by_proposal("PROP-1"),[self.row])
            sql,parameters=execute.call_args_list[0].args;self.assertIn(":id_propuesta",sql);self.assertNotIn("PROP-1",sql);self.assertEqual(parameters,{"id_propuesta":"PROP-1"})
            self.assertEqual(self.repository.list_by_proposal("EMPTY"),[])
            self.assertEqual(self.repository.get("doc-1"),self.row)

    def test_proposal_create_update_delete(self):
        with patch.object(self.repository.database,"execute_statement",return_value=response({"id":"PROP-1"})):
            self.assertTrue(self.repository.proposal_exists("PROP-1"))
        with patch.object(self.repository.database,"execute_write",return_value=[self.row]) as execute:
            self.assertEqual(self.repository.add(self.row),self.row)
            self.assertEqual(self.repository.update("doc-1",{"nombre_archivo":"b.pdf"}),self.row)
            self.assertEqual(self.repository.delete("doc-1"),self.row)
            self.assertIn("DELETE FROM documento_soporte",execute.call_args.args[0]);self.assertEqual(execute.call_args.args[1],{"id":"doc-1"})
        with patch.object(self.repository.database,"execute_write",return_value=0):
            self.assertIsNone(self.repository.delete("NO"))

    def test_postgresql_errors_and_sanitization(self):
        class Error(Exception):
            def __init__(self,code,message):self.response={"Error":{"DatabaseErrorCode":code,"Message":message}}
        for code,message,expected in [("23503","foreign key",self.repository.InvalidReferenceError),("23514","check constraint",self.repository.InvalidDocumentTypeError)]:
            with self.subTest(code=code),patch.object(self.repository.database,"execute_write",side_effect=Error(code,message)):
                with self.assertRaises(expected):self.repository.add(self.row)
        with patch.object(self.repository.database,"execute_statement",side_effect=RuntimeError("secret AWS detail")):
            with self.assertRaises(self.repository.RepositoryError) as caught:self.repository.get("doc-1")
            self.assertNotIn("secret AWS detail",str(caught.exception))


if __name__=="__main__":unittest.main()
