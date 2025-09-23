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
class VersionRequest(BaseModel):
    version : str
    version_type : str
    device_info : str

class VersionResponse(BaseModel):
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

@app.post("/", response_model=VersionResponse)
async def user_products(data: VersionRequest, db=Depends(connect_db), token : str = Depends(get_tokens)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT jwt_status FROM user_jwt WHERE jwt_token =%s",
        (token,)
    )
    token_query = db_cursor.fetchone()
    if token_query and token_query['jwt_status'] == 'valid':
        version = data.version
        version_type = data.version_type
        device_info = data.device_info

        db_cursor.execute(
            "SELECT app_version,app_version_type,app_url FROM app_version_check;",
        )
        verion_query_data = db_cursor.fetchall()
        if verion_query_data:
            print(verion_query_data)

        #     units_list = []
        #     for units_dict in units_query_data:
        #         units_list.append(units_dict)

        #     success_message = f"Units data found successfully"
        #     db_cursor.close()

        #     return_dict = {
        #         "units_data" : units_list
        #     }

        #     json_response = {
        #         "msg": success_message,"status":"Success","data":return_dict
        #     }

        #     return {"message": json_response}
        # else:
        #     db_cursor.close()
        #     failure_msg = "Invalid unit name"
        #     failure_response = {
        #         "msg": failure_msg,"status":"Failure","data":{}
        #     }
        #     return {"message": failure_response}
    else:
        db_cursor.close()
        failure_msg = "Token not valid, login again"
        failure_response = {
            "msg": failure_msg,"status":"Failure","data":{}
        }
        return {"message": failure_response}