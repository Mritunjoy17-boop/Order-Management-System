import os
import sys
from pydantic import BaseModel
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
class StocksRequest(BaseModel):
    product_code : str | None = None
    moulder_id : str | None = None
    current_godown : str | None = None

class StocksResponse(BaseModel):
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

@app.post("/", response_model=StocksResponse)
async def user_stocks(data: StocksRequest, db=Depends(connect_db), token : str = Depends(get_tokens)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT jwt_status FROM user_jwt WHERE jwt_token =%s",
        (token,)
    )
    token_query = db_cursor.fetchone()
    if token_query and token_query['jwt_status'] == 'valid':
        product_code = data.product_code
        moulder_id = data.moulder_id
        current_godown = data.current_godown

        db_cursor.execute(
            "SELECT barcode_id,lot_code,series_number,product_code,moulder_id,date_of_print,date_of_manufacture,date_of_sell,current_godown,date_time_last_update FROM stock WHERE product_code =%s AND moulder_id =%s AND current_godown =%s",
            (product_code,moulder_id,current_godown)
        )
        stocks_query_data = db_cursor.fetchall()
        if stocks_query_data:
            stocks_list = []
            for stocks_dict in stocks_query_data:
                stocks_list.append(stocks_dict)

            success_message = f"Stocks data found successfully"
            db_cursor.close()

            return_dict = {
                "stocks_data" : stocks_list
            }

            json_response = {
                "msg": success_message,"status":"Success","data":return_dict
            }

            return {"message": json_response}
        else:
            db_cursor.close()
            failure_msg = "Invalid product code or moulder id or current godown"
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