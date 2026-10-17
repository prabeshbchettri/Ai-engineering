from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType, NameEmail
file_path="src/data/products.json"
import json


def get_all_products():
    with open(file_path,'r') as p:
        return json.load(p)
    
    
def create_product(products):
    with open(file_path,'w') as p:
        json.dump(products,p)
        
        
conf = ConnectionConfig(
    MAIL_USERNAME="prabeshbchettri25@gmail.com",
    MAIL_PASSWORD="**********",
    MAIL_FROM="test@email.com",
    MAIL_PORT=465,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


async def simple_send(email: str):
    
    message = MessageSchema(
        subject="Fastapi-Mail module",
        recipients=email.model_dump().get("email"),
        body="<p>Thanks for using Fastapi-mail</p>",
        subtype=MessageType.html,
    )
    await FastMail(conf).send_message(message)
    return JSONResponse(status_code=200, content={"message": "email has been sent"})