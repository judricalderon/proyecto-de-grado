from enum import Enum
from pydantic import BaseModel,Field,ConfigDict
class Tipo(str,Enum):PROPUESTA="PROPUESTA";ACTA="ACTA";ANEXO="ANEXO";INFORME="INFORME";OTRO="OTRO"
class DocumentoIn(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True);tipo_documento:Tipo;nombre_archivo:str=Field(min_length=1);ruta:str=Field(min_length=1)
class DocumentoUpdate(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True);tipo_documento:Tipo|None=None;nombre_archivo:str|None=Field(default=None,min_length=1);ruta:str|None=Field(default=None,min_length=1)
