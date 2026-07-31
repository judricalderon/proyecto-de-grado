from copy import deepcopy

_INITIAL = [
    {"id": "USR-001", "nombre": "Ana Estudiante", "correo": "ana@example.com", "tipo_usuario": "ESTUDIANTE", "estado": "ACTIVO", "fecha_creacion": "2026-07-28T19:00:00Z", "fecha_ultimo_acceso": None},
    {"id": "USR-010", "nombre": "Diego Docente", "correo": "diego@example.com", "tipo_usuario": "DOCENTE", "estado": "ACTIVO", "fecha_creacion": "2026-07-28T19:00:00Z", "fecha_ultimo_acceso": None},
]
_items = deepcopy(_INITIAL)

def reset():
    global _items
    _items = deepcopy(_INITIAL)
def all(): return _items
def get(item_id): return next((x for x in _items if x["id"] == item_id), None)
def add(item): _items.append(item); return item
