from pydantic import BaseModel
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType, NameEmail

class CreateProduct(BaseModel):
    name:str
    price:int=0
    category:str
    stock:int=0
    
class UpdateProduct(BaseModel):
    name:str=None
    price:int=None
    category:str=None
    stock:int=None
    
class OrderSchema(BaseModel):
    count:int=0
    product_id:int=None
    email:str=None
    