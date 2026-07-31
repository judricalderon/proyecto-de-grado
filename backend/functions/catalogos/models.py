from enum import Enum
from pydantic import BaseModel,Field,ConfigDict
class TipoAgente(str,Enum): SOCRATICO="SOCRATICO";ORIENTADOR="ORIENTADOR";EVALUADOR="EVALUADOR";DOCUMENTAL="DOCUMENTAL"
class ModuloIn(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True);nombre:str=Field(min_length=1);descripcion:str=Field(min_length=1);orden:int=Field(gt=0);activo:bool=True
class FaseIn(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True);id_modulo:str;nombre:str=Field(min_length=1);descripcion:str=Field(min_length=1);orden:int=Field(gt=0);activo:bool=True
class AgenteIn(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True);nombre:str=Field(min_length=1);tipo_agente:TipoAgente;descripcion:str=Field(min_length=1);activo:bool=True
