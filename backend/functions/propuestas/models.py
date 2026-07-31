from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class EstadoPropuesta(str, Enum):
    BORRADOR="BORRADOR"; EN_REVISION="EN_REVISION"; APROBADA="APROBADA"; RECHAZADA="RECHAZADA"; CERRADA="CERRADA"
class PropuestaCreate(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    titulo_tentativo:str=Field(min_length=5)
    descripcion_inicial:str=Field(min_length=10)
class PropuestaUpdate(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    titulo_tentativo:str|None=Field(default=None,min_length=5)
    descripcion_inicial:str|None=Field(default=None,min_length=10)
    estado_general:EstadoPropuesta|None=None
class EstudianteCreate(BaseModel): id_estudiante:str=Field(min_length=1)
class DirectorCreate(BaseModel): id_docente:str=Field(min_length=1)
