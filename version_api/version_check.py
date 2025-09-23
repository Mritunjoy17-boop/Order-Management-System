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

@app.post("/", response_model=VersionResponse)
async def user_products(data: VersionRequest, db=Depends(connect_db)):
    version = data.version
    version_type = data.version_type
    device_info = data.device_info

    db_cursor = db.cursor(dictionary=True)

    db_cursor.execute(
        "SELECT app_version,app_version_type,app_url FROM app_version_check;",
    )
    version_query_data = db_cursor.fetchone()
    if version_query_data:
        is_update_required = False
        if float(version.strip()) > float(version_query_data['app_version'].strip()):
            is_update_required = True

        success_message = f"Version data found successfully"
        db_cursor.close()

        return_dict = {
            "is_update_required" : is_update_required,
            "app_url" : version_query_data['app_url'],
            "is_sync_required" : False
        }

        json_response = {
            "msg": success_message,"status":"Success","data":return_dict
        }

        return {"message": json_response}
    else:
        db_cursor.close()
        failure_msg = "No record of version exists"
        failure_response = {
            "msg": failure_msg,"status":"Failure","data":{}
        }
        return {"message": failure_response}