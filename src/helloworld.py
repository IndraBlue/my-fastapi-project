from fastapi import FastAPI

app = FastAPI()

#get api

@app.get("/")
def read_root():
    return {"message":"Hello, Indranil"}

#get with query parameters
@app.get("/items/{item_id}")
def read_item(item_id:int,q:str=None):
    return{"item_id":item_id,"query":q}


