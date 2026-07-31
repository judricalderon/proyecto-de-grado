# ADR-002: Repositorios en memoria

Estado: temporal.

Se usan listas y diccionarios reiniciables para validar contratos y reglas sin aprovisionar infraestructura. No se consideran persistencia real. Los servicios dependen de operaciones simples que podrán sustituirse por repositorios PostgreSQL/Aurora.
