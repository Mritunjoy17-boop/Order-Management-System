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
class MouldersRequest(BaseModel):
    moulder_id : str

class MouldersResponse(BaseModel):
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

@app.post("/", response_model=MouldersResponse)
async def user_products(data: MouldersRequest, db=Depends(connect_db), token : str = Depends(get_tokens)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT jwt_status FROM user_jwt WHERE jwt_token =%s",
        (token,)
    )
    token_query = db_cursor.fetchone()
    if token_query and token_query['jwt_status'] == 'valid':
        moulder_id = data.moulder_id

        db_cursor.execute(
            "SELECT moulder_id,moulder_name,moulder_keyphrase,is_active FROM moulders WHERE moulder_id =%s",
            (moulder_id,)
        )
        moulder_query_data = db_cursor.fetchall()
        if moulder_query_data:
            moulder_list = []
            for moulder_dict in moulder_query_data:
                moulder_list.append(moulder_dict)

            success_message = f"Moulder data found successfully"
            db_cursor.close()

            return_dict = {
                "moulders_data" : moulder_list
            }

            json_response = {
                "msg": success_message,"status":"Success","data":return_dict
            }

            return {"message": json_response}
        else:
            db_cursor.close()
            failure_msg = "Invalid moulder id"
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