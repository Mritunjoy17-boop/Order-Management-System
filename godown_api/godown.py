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
class GodownResponse(BaseModel):
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

@app.get("/", response_model=GodownResponse)
async def get_categories(db=Depends(connect_db), token : str = Depends(get_tokens)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT mobile_number,jwt_status FROM user_jwt WHERE jwt_token =%s",
        (token,)
    )
    token_query = db_cursor.fetchone()
    if token_query and token_query['jwt_status'] == 'valid':
        mobile_number = token_query['mobile_number']

        db_cursor.execute(
            "SELECT godown_id FROM user_godowns WHERE mobile_number =%s",
            (mobile_number,)
        )
        godown_id_query_data = db_cursor.fetchall()
        if godown_id_query_data:
            godown_id_list = []
            for godown_dict in godown_id_query_data:
                godown_id_list.append(godown_dict['godown_id'])

            godown_data_list = []
            for godown_id in godown_id_list: 
                db_cursor.execute(
                    "SELECT godown_id,godown_name,godown_type,sort_order,is_active FROM godowns WHERE godown_id =%s",
                    (godown_id,)
                )   
                godown_query_data = db_cursor.fetchall()
                if godown_query_data:
                    for godown_data in godown_query_data:
                        godown_data_list.append(godown_data)

            if godown_data_list:
                success_message = "Godown data found successfully"
                db_cursor.close()

                return_dict = {
                    "godown_data" : godown_data_list
                }

                json_response = {
                    "msg": success_message,"status":"Success","data":return_dict
                }

                return {"message": json_response}
            else:
                db_cursor.close()
                failure_msg = "Godown data not found"
                failure_response = {
                    "msg": failure_msg,"status":"Failure","data":{}
                }
                return {"message": failure_response}        
        else:
            db_cursor.close()
            failure_msg = "Godown id list not found"
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