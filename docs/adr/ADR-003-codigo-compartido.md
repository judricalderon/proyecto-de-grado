# ADR-003: Código compartido

Estado: aceptado temporalmente.

Cada `CodeUri` de SAM es independiente. Se mantienen utilidades HTTP pequeñas en cada `app.py` para que despliegue y pruebas tengan imports idénticos. No se crea Layer todavía: el ahorro sería pequeño y agregaría dos rutas de importación. Cuando crezcan respuestas, observabilidad y errores comunes, se migrarán a una Layer con estructura `python/` y `CompatibleRuntimes: [python3.11]`.
