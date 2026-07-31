from pydantic import BaseModel,Field,ConfigDict
class EvaluacionIn(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True)
 nivel_claridad:int=Field(ge=1,le=5);nivel_argumentacion:int=Field(ge=1,le=5);nivel_coherencia:int=Field(ge=1,le=5);fortalezas:str=Field(min_length=1);aspectos_por_fortalecer:str=Field(min_length=1);observaciones:str=""
