import os
import sys
from datetime import datetime
from pydantic import BaseModel
from typing import List
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI,HTTPException,Depends,status,Header, Body
from fastapi.exceptions import RequestValidationError

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from db_config import connect_db

app = FastAPI()

#pydantic models
class StocksMovementRequest(BaseModel):
    batch_id : str | None
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
async def submit_inward_outward(data: List[StocksMovementRequest], db=Depends(connect_db), token: str = Depends(get_tokens)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT jwt_status FROM user_jwt WHERE jwt_token =%s",
        (token,)
    )
    token_query = db_cursor.fetchone()
    if token_query and token_query['jwt_status'] == 'valid':
        inward_outward_data = [obj.dict() for obj in data]

        success_flag = 0
        try:
            for movement_data in inward_outward_data:
                batch_id = movement_data.get('batch_id')
                if batch_id == '':
                    batch_id = None
                godown_id = movement_data.get('godown_id')
                product_code = movement_data.get('product_code')
                barcode_id = movement_data.get('barcode_id')
                movement_type = movement_data.get('movement_type')
                comments = movement_data.get('comments')
                datetime_obj = datetime.now()
                datetime_timestamp = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")

                db_cursor.execute(
                    "INSERT INTO stock_movement(batch_id,godown_id,product_code,barcode_id,movement_type,comments,datetime_timestamp)VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (batch_id, godown_id, product_code, barcode_id, movement_type, comments, datetime_timestamp)
                )
                db.commit()
        except Exception as e:
            final_message = f"Error occured : {e}"
        else:
            final_message = f"Inward/Outward data inserted successfully"
            success_flag = 1

        if success_flag:
            success_message = f"Stocks movement data inserted successfully"
            db_cursor.close()

            json_response = {
                "msg": success_message, "status": "Success", "data": {}
            }

            return {"message": json_response}
        else:
            db_cursor.close()
            failure_msg = final_message
            failure_response = {
                "msg": failure_msg, "status": "Failure", "data": {}
            }
            return {"message": failure_response}
    else:
        db_cursor.close()
        failure_msg = "Token expired"
        failure_response = {
            "msg": failure_msg, "status": "Failure", "data": {}
        }
        
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = failure_response
        )