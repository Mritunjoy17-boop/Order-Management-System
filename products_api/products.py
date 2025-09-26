import os
import sys
from pydantic import BaseModel
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI,HTTPException,Depends,status,Header
from fastapi.exception_handlers import RequestValidationError

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from db_config import connect_db

app = FastAPI()

#pydantic models
class ProductsRequest(BaseModel):
    product_category : str | None = None

class ProductsResponse(BaseModel):
    message : dict

#Dependency to extract tokens from headers
def get_tokens(authorization : str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid authorization header format"
        )
    token = authorization.split(" ")[1]
    return token

@app.post("/", response_model=ProductsResponse)
async def user_products(data: ProductsRequest, db=Depends(connect_db), token : str = Depends(get_tokens)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT jwt_status FROM user_jwt WHERE jwt_token =%s",
        (token,)
    )
    token_query = db_cursor.fetchone()
    if token_query and token_query['jwt_status'] == 'valid':
        if not data.product_category:
            db_cursor.execute(
                "SELECT product_code,product_picture,product_name,product_category,product_primary_unit,product_secondary_unit FROM products",
            )
        else:    
            db_cursor.execute(
                "SELECT product_code,product_picture,product_name,product_category,product_primary_unit,product_secondary_unit FROM products WHERE product_category = %s",
                (data.product_category,)
            )
        query_data = db_cursor.fetchall()
        if query_data:
            products_list = []
            for prod_dict in query_data:
                products_list.append(prod_dict)

            print(products_list)

            success_message = f"Products data found"
            db_cursor.close()

            return_dict = {
                "products_data" : products_list
            }

            json_response = {
                "msg": success_message,"status":"Success","data":return_dict
            }

            return {"message": json_response}
        else:
            db_cursor.close()
            failure_msg = "Invalid mobile number or product code"
            failure_response = {
                "msg": failure_msg,"status":"Failure","data":{}
            }
            return {"message": failure_response}
    else:
        db_cursor.close()
        failure_msg = "Token not valid, login again"
        failure_response = {
            "msg": failure_msg,"status":"Failure","data":{}
        }
        return {"message": failure_response}