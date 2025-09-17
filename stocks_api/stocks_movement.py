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
class StocksMovementRequest(BaseModel):
    batch_id : str
    godown_id : str
    product_code : str
    barcode_id : str
    movement_type : str
    comments : str | None = None

class StocksMovementResponse(BaseModel):
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

@app.post("/", response_model=StocksMovementResponse)
async def user_stocks(data: StocksMovementRequest, db=Depends(connect_db), token : str = Depends(get_tokens)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT jwt_status FROM user_jwt WHERE jwt_token =%s",
        (token,)
    )
    token_query = db_cursor.fetchone()
    if token_query and token_query['jwt_status'] == 'valid':
        batch_id = data.batch_id
        godown_id = data.godown_id
        product_code = data.product_code
        barcode_id = data.barcode_id
        movement_type = data.movement_type
        datetime_obj = datetime.now()
        comments = data.comments
        datetime_timestamp = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")

        db_cursor.execute(
            "INSERT INTO stock_movement(batch_id,godown_id,product_code,barcode_id,movement_type,comments,datetime_timestamp)VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            (batch_id,godown_id,product_code,barcode_id,movement_type,comments,datetime_timestamp)
        )
        db.commit()
        if db_cursor.rowcount > 0:
            success_message = f"Stocks movement data inserted successfully"
            db_cursor.close()

            json_response = {
                "msg": success_message,"status":"Success","data":{}
            }

            return {"message": json_response}
        else:
            db_cursor.close()
            failure_msg = "Invalid barcode id"
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