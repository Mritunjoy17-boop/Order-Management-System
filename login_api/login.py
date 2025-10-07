import os
import sys
from pydantic import BaseModel
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI,HTTPException,Depends,status, Header
from fastapi.exception_handlers import RequestValidationError
from login_api.jwt_token_handler import create_access_token

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from db_config import connect_db

app = FastAPI()

#pydantic models
class LoginRequest(BaseModel):
    mobile_number : str
    password : str

class LoginResponse(BaseModel):
    message : dict

@app.post("/", response_model=LoginResponse)
async def user_login(data: LoginRequest, request: Request, db=Depends(connect_db), device_id: str = Header(None)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT mobile_number,password,user_name,user_type,is_active FROM users WHERE mobile_number=%s AND password=%s",
        (data.mobile_number, data.password)
    )
    data = db_cursor.fetchone()
    if data:
        mobile_number = data['mobile_number']
        password = data['password']
        user = data['user_name']
        user_type = data['user_type']
        is_active = data['is_active']

        memo_message = f"Logged in successfully"
        db_cursor.execute("UPDATE users SET text_memo = %s WHERE user_name = %s",
                        (memo_message, user)
        )
        db.commit()
        
        is_active = True if is_active == 1 else False

        token_data = {
            "sub": user,
            "mobile_number": mobile_number,
            "user_type": user_type
        }
        access_token = create_access_token(token_data)
        if not device_id:
            device_id = f"device_{os.urandom(4).hex()}"

        #to check if data exists with a specific mobile number
        db_cursor.execute(
            "SELECT mobile_number,device_id FROM user_jwt WHERE mobile_number =%s",
            (mobile_number, )
        )
        token_query_result = db_cursor.fetchone()
        if token_query_result:
            if token_query_result.get('mobile_number','') and token_query_result.get('device_id',''):
                db_cursor.execute(
                    "UPDATE user_jwt SET jwt_token =%s, jwt_status = 'valid' WHERE mobile_number =%s and device_id = %s",
                    (access_token, mobile_number, device_id)
                )
            else:
                db_cursor.execute(
                    "INSERT INTO user_jwt(mobile_number,jwt_token,jwt_status,device_id) VALUES(%s,%s,'valid',%s)",
                    (mobile_number, access_token, device_id)
                )    
        else:
            db_cursor.execute(
                "INSERT INTO user_jwt(mobile_number,jwt_token,jwt_status,device_id) VALUES(%s,%s,'valid',%s)",
                (mobile_number, access_token, device_id)
            )

        db.commit()
        db_cursor.close()

        return_dict = {
            "user_data" : {
                "mobile_number" : mobile_number,
                "user_name" : user,
                "user_type" : user_type,
                "is_active" : is_active,
            },
            "access_token": "Bearer " + access_token,
            "token_type":"bearer"
        }

        json_response = {
            "msg": memo_message,"status":"Success","data":return_dict
        }

        return {"message": json_response}
    else:
        db_cursor.close()
        failure_msg = "Invalid username or password"
        failure_response = {
            "msg": failure_msg,"status":"Failure","data":{}
        }
        return {"message": failure_response}