BEGIN;

CREATE TABLE usuario (
    id VARCHAR(64) PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL CHECK (char_length(btrim(nombre)) >= 3),
    correo VARCHAR(320) NOT NULL UNIQUE,
    tipo_usuario VARCHAR(20) NOT NULL CHECK (tipo_usuario IN ('ESTUDIANTE', 'DOCENTE', 'ADMIN')),
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO', 'INACTIVO')),
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_ultimo_acceso TIMESTAMPTZ
);

CREATE TABLE propuesta_proyecto (
    id VARCHAR(64) PRIMARY KEY,
    titulo_tentativo VARCHAR(300) NOT NULL CHECK (char_length(btrim(titulo_tentativo)) >= 5),
    descripcion_inicial TEXT NOT NULL CHECK (char_length(btrim(descripcion_inicial)) >= 10),
    estado_general VARCHAR(20) NOT NULL DEFAULT 'BORRADOR'
        CHECK (estado_general IN ('BORRADOR', 'EN_REVISION', 'APROBADA', 'RECHAZADA', 'CERRADA')),
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE propuesta_estudiante (
    id VARCHAR(64) PRIMARY KEY,
    id_propuesta VARCHAR(64) NOT NULL REFERENCES propuesta_proyecto(id) ON DELETE RESTRICT,
    id_estudiante VARCHAR(64) NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
    UNIQUE (id_propuesta, id_estudiante)
);

CREATE TABLE propuesta_director (
    id VARCHAR(64) PRIMARY KEY,
    id_propuesta VARCHAR(64) NOT NULL REFERENCES propuesta_proyecto(id) ON DELETE RESTRICT,
    id_docente VARCHAR(64) NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
    fecha_asignacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO', 'INACTIVO'))
);
CREATE UNIQUE INDEX uq_propuesta_director_activo
    ON propuesta_director (id_propuesta) WHERE estado = 'ACTIVO';

CREATE TABLE modulo (
    id VARCHAR(64) PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT NOT NULL,
    orden INTEGER NOT NULL CHECK (orden > 0),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE UNIQUE INDEX uq_modulo_orden_activo ON modulo (orden) WHERE activo;

CREATE TABLE fase (
    id VARCHAR(64) PRIMARY KEY,
    id_modulo VARCHAR(64) NOT NULL REFERENCES modulo(id) ON DELETE RESTRICT,
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT NOT NULL,
    orden INTEGER NOT NULL CHECK (orden > 0),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE UNIQUE INDEX uq_fase_modulo_orden_activa ON fase (id_modulo, orden) WHERE activo;

CREATE TABLE progreso_fase (
    id VARCHAR(64) PRIMARY KEY,
    id_propuesta VARCHAR(64) NOT NULL REFERENCES propuesta_proyecto(id) ON DELETE RESTRICT,
    id_fase VARCHAR(64) NOT NULL REFERENCES fase(id) ON DELETE RESTRICT,
    estado VARCHAR(20) NOT NULL CHECK (estado IN ('NO_INICIADA', 'EN_PROGRESO', 'COMPLETADA')),
    porcentaje_avance INTEGER NOT NULL CHECK (porcentaje_avance BETWEEN 0 AND 100),
    fecha_inicio TIMESTAMPTZ,
    fecha_ultima_actualizacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre TIMESTAMPTZ,
    UNIQUE (id_propuesta, id_fase),
    CHECK (
        (estado = 'NO_INICIADA' AND porcentaje_avance = 0) OR
        (estado = 'EN_PROGRESO' AND porcentaje_avance BETWEEN 1 AND 99) OR
        (estado = 'COMPLETADA' AND porcentaje_avance = 100)
    )
);

CREATE TABLE agente (
    id VARCHAR(64) PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    tipo_agente VARCHAR(20) NOT NULL CHECK (tipo_agente IN ('SOCRATICO', 'ORIENTADOR', 'EVALUADOR', 'DOCUMENTAL')),
    descripcion TEXT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE UNIQUE INDEX uq_agente_nombre_activo ON agente (lower(nombre)) WHERE activo;

CREATE TABLE evaluacion_estado (
    id VARCHAR(64) PRIMARY KEY,
    id_propuesta VARCHAR(64) NOT NULL REFERENCES propuesta_proyecto(id) ON DELETE RESTRICT,
    id_fase VARCHAR(64) NOT NULL REFERENCES fase(id) ON DELETE RESTRICT,
    nivel_claridad SMALLINT NOT NULL CHECK (nivel_claridad BETWEEN 1 AND 5),
    nivel_argumentacion SMALLINT NOT NULL CHECK (nivel_argumentacion BETWEEN 1 AND 5),
    nivel_coherencia SMALLINT NOT NULL CHECK (nivel_coherencia BETWEEN 1 AND 5),
    fortalezas TEXT NOT NULL,
    aspectos_por_fortalecer TEXT NOT NULL,
    observaciones TEXT NOT NULL DEFAULT '',
    fecha_evaluacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documento_soporte (
    id VARCHAR(64) PRIMARY KEY,
    id_propuesta VARCHAR(64) NOT NULL REFERENCES propuesta_proyecto(id) ON DELETE RESTRICT,
    tipo_documento VARCHAR(20) NOT NULL CHECK (tipo_documento IN ('PROPUESTA', 'ACTA', 'ANEXO', 'INFORME', 'OTRO')),
    nombre_archivo VARCHAR(500) NOT NULL,
    ruta TEXT NOT NULL,
    fecha_carga TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_propuesta_estudiante_estudiante ON propuesta_estudiante (id_estudiante);
CREATE INDEX idx_propuesta_director_docente ON propuesta_director (id_docente);
CREATE INDEX idx_fase_modulo ON fase (id_modulo);
CREATE INDEX idx_progreso_fase_fase ON progreso_fase (id_fase);
CREATE INDEX idx_evaluacion_propuesta_fase_fecha ON evaluacion_estado (id_propuesta, id_fase, fecha_evaluacion DESC);
CREATE INDEX idx_documento_propuesta ON documento_soporte (id_propuesta);

COMMIT;
