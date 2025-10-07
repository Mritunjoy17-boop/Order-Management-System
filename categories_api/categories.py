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
class CategoriesResponse(BaseModel):
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

@app.get("/", response_model=CategoriesResponse)
async def get_categories(db=Depends(connect_db), token : str = Depends(get_tokens)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT jwt_status FROM user_jwt WHERE jwt_token =%s",
        (token,)
    )
    token_query = db_cursor.fetchone()
    if token_query and token_query['jwt_status'] == 'valid':
        db_cursor.execute(
            "SELECT category_id,category_name,sort_order,is_active FROM category"
        )
        query_data = db_cursor.fetchall()
        if query_data:
            categories_list = []
            for cat_dict in query_data:
                categories_list.append(cat_dict)

            success_message = "Categories data found"
            db_cursor.close()

            return_dict = {
                "categories_data" : categories_list
            }

            json_response = {
                "msg": success_message,"status":"Success","data":return_dict
            }

            return {"message": json_response}
        else:
            db_cursor.close()
            failure_msg = "Invalid category id"
            failure_response = {
                "msg": failure_msg,"status":"Failure","data":{}
            }
            return {"message": failure_response}
    else:
        db_cursor.close()
        failure_msg = "Token expired"
        failure_response = {
            "msg": failure_msg,"status":"Failure","data":{}
        }
        
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = failure_response
        )