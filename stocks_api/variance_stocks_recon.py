import logging
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

# Define log file path
log_file = os.path.expanduser("~/logs/app.log")

# Configure logging
logging.basicConfig(
    filename=log_file,
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.ERROR
)

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
                try:
                    product_code = temp_data['product_code']
                    expected_product_count = temp_data['expected_product_count']
                    actual_product_count = temp_data['actual_product_count']
                    product_variance = int(temp_data['expected_product_count']) - int(temp_data['actual_product_count'])
                    if int(expected_product_count) > int(actual_product_count):
                        product_variance = '-' + str(product_variance)
                    else:
                        product_variance = str(product_variance).replace('-','+')

                    print(product_code,expected_product_count,actual_product_count,product_variance)

                    db_cursor.execute(
                        "SELECT product_code FROM stock_variance WHERE product_code =%s;",
                        (product_code,)
                    )
                    product_code_query = db_cursor.fetchone()
                    if product_code_query:
                        print(123)
                        #updating data to stock_variance
                        db_cursor.execute(
                            "UPDATE stock_variance SET expected_count =%s,actual_count =%s, variance = %s,datetime_timestamp = NOW() WHERE product_code = %s",
                            (expected_product_count,actual_product_count,product_variance,product_code)
                        )
                        db.commit()
                    else:
                        print(456)
                        #inserting data to stock_variance
                        db_cursor.execute(
                            "INSERT INTO stock_variance(product_code,expected_count,actual_count,variance)VALUES(%s,%s,%s,%s);",
                            (product_code,expected_product_count,actual_product_count,product_variance)
                        )
                        db.commit()
                except Exception as e:
                    logging.error(f"Data not submitted for {product_code}", exc_info=True)
                    continue

            success_message = f"Variance data of stocks reconcilation updated/inserted successfully"
            db_cursor.close()

            json_response = {
                "msg": success_message,"status":"Success","data":{}
            }

            return {"message": json_response}
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