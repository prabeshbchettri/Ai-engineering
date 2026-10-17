from fastapi import FastAPI
from src.routes.ProductRoute import ProductRoutes

app=FastAPI(
    title="practice fastapi",
    description="learning fastapi"
)

@app.get("/")
def root():
    return {
        "message":"Welcome to practice fastapi"
    }

@app.get("/home")
def home():
    return {
        "message":"Keep learning!"
    }
    
    
    
app.include_router(ProductRoutes,prefix="/products")
    
# CRUD APIs - product  now using json file

