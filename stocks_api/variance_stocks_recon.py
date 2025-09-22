import os
import sys
from datetime import datetime
from pydantic import BaseModel
from typing import List
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI,HTTPException,Depends,status,Header
from fastapi.exceptions import RequestValidationError

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from db_config import connect_db

app = FastAPI()

#pydantic models
class VarianceRequest(BaseModel):
    product_code : str
    expected_product_count : str
    actual_product_count : str

class VarianceResponse(BaseModel):
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

@app.post("/", response_model=VarianceResponse)
async def variance_stocks_reconcilation(data: List[VarianceRequest], db=Depends(connect_db), token : str = Depends(get_tokens)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT jwt_status FROM user_jwt WHERE jwt_token =%s",
        (token,)
    )
    token_query = db_cursor.fetchone()
    if token_query and token_query['jwt_status'] == 'valid':
        actual_data_list = [actual_data.dict() for actual_data in data]
            
        if actual_data_list:
            for temp_data in actual_data_list:
                product_code = temp_data['product_code']
                expected_product_count = temp_data['expected_product_count']
                actual_product_count = temp_data['actual_product_count']
                product_variance = int(temp_data['expected_product_count']) - int(temp_data['actual_product_count'])
                
                print(product_code,expected_product_count,actual_product_count,product_variance)

            # success_message = f"Variance data of stocks reconcilation found successfully"
            # db_cursor.close()

            # return_dict = {
            #     "variance_reconcilation_data" : variance_list
            # }

            # json_response = {
            #     "msg": success_message,"status":"Success","data":return_dict
            # }

            # return {"message": json_response}
        else:
            db_cursor.close()
            failure_msg = "No expected data found for reconcilation variance"
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