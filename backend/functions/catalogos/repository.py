from copy import deepcopy
_M=[{"id":"MOD-001","nombre":"Desarrollo de propuestas de proyectos","descripcion":"Módulo inicial","orden":1,"activo":True}]
_N=["Exploración inicial","Situación a intervenir","Justificación","Objetivos","Metodología","Viabilidad","Evaluación del estado actual"]
_F=[{"id":f"FASE-{i:03}","id_modulo":"MOD-001","nombre":n,"descripcion":n,"orden":i,"activo":True} for i,n in enumerate(_N,1)];_A=[]
def reset():
 global modulos,fases,agentes;modulos=deepcopy(_M);fases=deepcopy(_F);agentes=deepcopy(_A)
reset()
def get(items,i):return next((x for x in items if x["id"]==i),None)
