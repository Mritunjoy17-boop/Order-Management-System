import os
import sys
from datetime import datetime
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
class StocksReconcilationRequest(BaseModel):
    godown_id : str
    category_id : str

class StocksReconcilationResponse(BaseModel):
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

@app.post("/", response_model=StocksReconcilationResponse)
async def user_stocks(data: StocksReconcilationRequest, db=Depends(connect_db), token : str = Depends(get_tokens)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT jwt_status FROM user_jwt WHERE jwt_token =%s",
        (token,)
    )
    token_query = db_cursor.fetchone()
    if token_query and token_query['jwt_status'] == 'valid':
        godown_id = data.godown_id
        category_id = data.category_id

        db_cursor.execute(
            "SELECT prod.product_name, prod.product_code, COUNT(sm.record_id) AS movement_count FROM stock_movement sm INNER JOIN products prod ON sm.product_code = prod.product_code INNER JOIN category cat ON prod.product_category = cat.category_id WHERE sm.godown_id =%s AND cat.category_id =%s GROUP BY prod.product_code, prod.product_name",
            (godown_id,category_id)
        )
        stock_reconcilation_data = db_cursor.fetchall()
        if stock_reconcilation_data:
            print(stock_reconcilation_data)
            success_message = f"Stocks reconcilation data found successfully"
            db_cursor.close()

            return_dict = {
                "reconcilation_data" : stock_reconcilation_data
            }

            json_response = {
                "msg": success_message,"status":"Success","data":{return_dict}
            }

            return {"message": json_response}
        else:
            db_cursor.close()
            failure_msg = "Invalid godown id and category id"
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