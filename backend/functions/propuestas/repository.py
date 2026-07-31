from copy import deepcopy
_P=[{"id":"PROP-001","titulo_tentativo":"Sistema de acompañamiento para proyectos de grado","descripcion_inicial":"Plataforma para apoyar proyectos de grado.","estado_general":"BORRADOR","fecha_creacion":"2026-07-28T19:00:00Z","fecha_actualizacion":"2026-07-28T19:00:00Z"}]
_U={"USR-001":{"tipo_usuario":"ESTUDIANTE","estado":"ACTIVO"},"USR-002":{"tipo_usuario":"ESTUDIANTE","estado":"ACTIVO"},"USR-010":{"tipo_usuario":"DOCENTE","estado":"ACTIVO"},"USR-X":{"tipo_usuario":"ESTUDIANTE","estado":"INACTIVO"}}
_E=[{"id":"REL-001","id_propuesta":"PROP-001","id_estudiante":"USR-001"}]; _D=[]
def reset():
 global propuestas,estudiantes,directores; propuestas=deepcopy(_P); estudiantes=deepcopy(_E); directores=deepcopy(_D)
reset()
def get(collection,item_id): return next((x for x in collection if x["id"]==item_id),None)
