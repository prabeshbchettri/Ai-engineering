from fastapi import APIRouter,HTTPException
from src.utils.utils import get_all_products, create_product,simple_send
from src.dtos.Productschema import CreateProduct,OrderSchema,UpdateProduct
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType, NameEmail

ProductRoutes = APIRouter()


@ProductRoutes.get("/")
def getAllProducts():
    return get_all_products()

@ProductRoutes.get("/{id}")
def getOneProduct(id:int):
    allProducts=get_all_products()
    for product in allProducts:
        if product["id"]==id:
            return product
        
    return HTTPException(status_code=400,detail={"error":"product not found"})
    

@ProductRoutes.post("/create")
def CreateNewProduct(product:CreateProduct):
    products=get_all_products()
    product=product.model_dump()
    next_id=max([p["id"] for p in products])+1
    product["id"]=next_id
    products.append(product)
    create_product(products)
    return {"messages":"New product created successfully"}

@ProductRoutes.put("/update/{id}")
def updateProduct(product:UpdateProduct,id:int=None):
    if not id:
        return HTTPException(status_code=400,detail={"error":"Product id did not found"})
    
    oneProduct=None
    allProducts=get_all_products()
    for index,p in enumerate(allProducts):
        if p["id"]==id:
            changes={}
            for k,v in product.model_dump().items():
                if v is not None:
                    changes[k]=v
                    
                
            allProducts[index]={"id":id,**p,**product.model_dump()}
            create_product(allProducts)
            return {"messages":"Product updated succesfully"}
    return HTTPException(status_code=400,detail={"error":"product not found to be updated"})




@ProductRoutes.delete("/delete/{id}")
def deleteProduct(id:int=None):
    if not id:
        return HTTPException(status_code=400,detail={"error":"Product id did not found"})
    allProducts=get_all_products()
    for index,p in enumerate(allProducts):
        if p["id"]==id:
            allProducts.pop(index)
            create_product(allProducts)
            return {"message":"Product deleted successfully"}
        
    return HTTPException(status_code=400,detail={"error":"product not found"})
    
    


@ProductRoutes.post("/order")
async def placeOrder(orderDetails:OrderSchema):
    count=orderDetails.count
    product_id=orderDetails.product_id
    email=orderDetails.email
    
    allProducts=get_all_products()
    for index,p in enumerate(allProducts):
        if p["id"]==product_id:
            oneProduct=p
            break
    if not oneProduct:
        return HTTPException(status_code=400,detail={"error":"product not found"})
            
    if oneProduct["stock"]< count:
        return HTTPException(status_code=400,detail={"error":"stock not sufficient"})
        
        
        
        
    return{"message":"Order placed successfully"}
    
# Data needed- product_id,count:,email_address
# three condition -> product_id is correct , count is adequate ie count<=stock, send mail to given email address


