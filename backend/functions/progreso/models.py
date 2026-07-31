from enum import Enum
from pydantic import BaseModel,Field,model_validator
class Estado(str,Enum):NO_INICIADA="NO_INICIADA";EN_PROGRESO="EN_PROGRESO";COMPLETADA="COMPLETADA"
class ProgresoIn(BaseModel):
 id_fase:str;estado:Estado;porcentaje_avance:int=Field(ge=0,le=100)
 @model_validator(mode="after")
 def coherent(self):
  ok=(self.estado==Estado.NO_INICIADA and self.porcentaje_avance==0) or (self.estado==Estado.EN_PROGRESO and 1<=self.porcentaje_avance<=99) or (self.estado==Estado.COMPLETADA and self.porcentaje_avance==100)
  if not ok:raise ValueError("El porcentaje no corresponde al estado")
  return self
class ProgresoUpdate(BaseModel):
 estado:Estado;porcentaje_avance:int=Field(ge=0,le=100)
 @model_validator(mode="after")
 def coherent(self):
  ok=(self.estado==Estado.NO_INICIADA and self.porcentaje_avance==0) or (self.estado==Estado.EN_PROGRESO and 1<=self.porcentaje_avance<=99) or (self.estado==Estado.COMPLETADA and self.porcentaje_avance==100)
  if not ok:raise ValueError("El porcentaje no corresponde al estado")
  return self
