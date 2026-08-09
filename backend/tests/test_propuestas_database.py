import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROPOSALS = Path(__file__).resolve().parents[1] / "functions" / "propuestas"


def response(row=None):
    if row is None:
        return {"columnMetadata": [], "records": []}
    return {
        "columnMetadata": [{"name": key} for key in row],
        "records": [[{"isNull": True} if value is None else {"stringValue": value} for value in row.values()]],
    }


class PropuestasDatabaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for name in ("repository", "database"):
            sys.modules.pop(name, None)
        sys.path.insert(0, str(PROPOSALS))
        cls.database = importlib.import_module("database")
        cls.repository = importlib.import_module("repository")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(PROPOSALS))

    @patch.dict(os.environ, {"DB_CLUSTER_ARN":"cluster","DB_SECRET_ARN":"secret","DB_NAME":"db"})
    @patch("database.boto3.client")
    def test_data_api_parameters_and_transaction_helpers(self, client):
        rds=client.return_value;rds.execute_statement.return_value={"records":[]};rds.begin_transaction.return_value={"transactionId":"tx"}
        self.database.execute_statement("SELECT :id",{"id":"PROP-1"})
        self.assertEqual(rds.execute_statement.call_args.kwargs["parameters"][0]["value"],{"stringValue":"PROP-1"})
        self.assertEqual(self.database.begin_transaction(),"tx")
        self.database.commit_transaction("tx");self.database.rollback_transaction("tx")
        self.assertNotIn("database",rds.commit_transaction.call_args.kwargs)

    def test_crud_queries_are_parameterized(self):
        proposal={"id":"p1","titulo_tentativo":"Título","descripcion_inicial":"Descripción larga","estado_general":"BORRADOR","fecha_creacion":"2026-01-01T00:00:00Z","fecha_actualizacion":"2026-01-01T00:00:00Z"}
        with patch.object(self.repository.database,"execute_statement",return_value=response(proposal)) as read, patch.object(self.repository.database,"execute_write",return_value=[proposal]) as write:
            self.assertEqual(self.repository.all_proposals(),[proposal])
            self.assertEqual(self.repository.get_proposal("p1"),proposal)
            self.assertEqual(self.repository.add_proposal(proposal),proposal)
            self.assertEqual(self.repository.update_proposal("p1",{"titulo_tentativo":"Nuevo"},"now"),proposal)
            self.assertEqual(self.repository.close_proposal("p1","now"),proposal)
            self.assertIn(":id",read.call_args_list[-1].args[0])
            self.assertIn(":titulo_tentativo",write.call_args_list[-2].args[0])
        with patch.object(self.repository.database,"execute_write",return_value=0):
            self.assertIsNone(self.repository.update_proposal("missing",{},"now"))

    def test_students_users_and_director(self):
        relation={"id":"r1","id_propuesta":"p1","id_estudiante":"u1"}
        director={"id":"d1","id_propuesta":"p1","id_docente":"u2","fecha_asignacion":"now","estado":"ACTIVO"}
        student_profile={"id":"u1","nombre":"Ana","correo":"ana@example.com","tipo_usuario":"ESTUDIANTE","estado":"ACTIVO","fecha_creacion":"now","fecha_ultimo_acceso":None}
        director_profile={"id":"u2","nombre":"Docente","correo":"doc@example.com","tipo_usuario":"DOCENTE","estado":"ACTIVO","fecha_creacion":"now","fecha_ultimo_acceso":None}
        with patch.object(self.repository.database,"execute_statement",side_effect=[response(student_profile),response(),response(director_profile),response()]), patch.object(self.repository.database,"execute_write",side_effect=[[relation],[director],[director]]):
            self.assertEqual(self.repository.list_students("p1"),[student_profile])
            self.assertEqual(self.repository.add_student(relation),relation)
            self.assertEqual(self.repository.add_director(director),director)
            self.assertEqual(self.repository.deactivate_director("p1"),director)
        with patch.object(self.repository.database,"execute_write",return_value=0):
            with self.assertRaises(self.repository.DuplicateStudentError):self.repository.add_student(relation)

    def test_remove_student_commits_and_rolls_back(self):
        proposal={"estado_general":"BORRADOR"};relation={"id":"r1","id_propuesta":"p1","id_estudiante":"u1"}
        with patch.object(self.repository.database,"begin_transaction",return_value="tx"), patch.object(self.repository.database,"execute_statement",side_effect=[response(proposal),response(relation)]), patch.object(self.repository.database,"execute_write",return_value=1), patch.object(self.repository.database,"commit_transaction") as commit, patch.object(self.repository.database,"rollback_transaction") as rollback:
            self.repository.remove_student("p1","u1");commit.assert_called_once_with("tx");rollback.assert_not_called()
        proposal["estado_general"]="EN_REVISION"
        with patch.object(self.repository.database,"begin_transaction",return_value="tx"), patch.object(self.repository.database,"execute_statement",side_effect=[response(proposal),response(relation)]), patch.object(self.repository.database,"rollback_transaction") as rollback:
            with self.assertRaises(self.repository.LastStudentRequiredError):self.repository.remove_student("p1","u1")
            rollback.assert_called_once_with("tx")

    def test_unexpected_data_api_error_is_sanitized(self):
        with patch.object(self.repository.database,"execute_statement",side_effect=RuntimeError("secret AWS detail")):
            with self.assertRaises(self.repository.RepositoryError) as caught:self.repository.all_proposals()
            self.assertNotIn("secret AWS detail",str(caught.exception))


if __name__=="__main__":unittest.main()
