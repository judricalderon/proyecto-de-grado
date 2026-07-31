from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re

class TipoUsuario(str, Enum):
    ESTUDIANTE = "ESTUDIANTE"
    DOCENTE = "DOCENTE"
    ADMIN = "ADMIN"

class EstadoUsuario(str, Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"

class UsuarioCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    nombre: str = Field(min_length=3)
    correo: str
    tipo_usuario: TipoUsuario

    @field_validator("correo")
    @classmethod
    def correo_valido(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("correo inválido")
        return value

class UsuarioUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    nombre: str | None = Field(default=None, min_length=3)
    correo: str | None = None
    tipo_usuario: TipoUsuario | None = None
    estado: EstadoUsuario | None = None

    @field_validator("correo")
    @classmethod
    def correo_valido(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("correo inválido")
        return value
