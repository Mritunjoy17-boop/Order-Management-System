import os
import sys
from pydantic import BaseModel,field_validator,model_validator,field_serializer
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
    device_token: str | None = None

    @field_validator('mobile_number')
    @classmethod
    def validate_mobile_number(cls,value):
        if len(value) != 10:
            raise ValueError("Mobile number must be 10 digits long")
        return value

    # @model_validator(mode = 'after')
    # def validate_password(self):
    #     if self.password != self.confirm_password:
    #         raise ValueError("Password and confirm password do not match")
    #     return self

class LoginResponse(BaseModel):
    message : dict

    # @field_serializer("message")
    # def serialize_message(self, value):
    #     return {"msg": value, "status": "Success", "data": {}, "type": "LoginResponse"}


@app.post("/", response_model=LoginResponse)
async def user_login(data: LoginRequest, db=Depends(connect_db)):
    db_cursor = db.cursor(dictionary=True, buffered = True)
    db_cursor.execute(
        "SELECT mobile_number,password,user_name,user_type,is_active FROM users WHERE mobile_number=%s AND password=%s",
        (data.mobile_number, data.password)
    )
    user_data = db_cursor.fetchone()
    if user_data:
        mobile_number = user_data['mobile_number']
        password = user_data['password']
        user = user_data['user_name']
        user_type = user_data['user_type']
        is_active = user_data['is_active']

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

        #to check if data exists with a specific mobile number
        db_cursor.execute(
            "SELECT mobile_number,jwt_status FROM user_jwt WHERE mobile_number =%s",
            (mobile_number, )
        )
        token_query_result = db_cursor.fetchone()
        if token_query_result:
            db_cursor.execute(
                    "UPDATE user_jwt SET jwt_token =%s, jwt_status = 'valid' WHERE mobile_number =%s",
                    (access_token, mobile_number)
                ) 
            # if token_query_result.get('jwt_status','') == 'valid':
            #     db_cursor.close()
            #     failure_msg = "User already logged in"
            #     failure_response = {
            #         "msg": failure_msg,"status":"Failure","data":{}
            #     }
            #     return {"message": failure_response}
            # else:
            #     db_cursor.execute(
            #         "UPDATE user_jwt SET jwt_token =%s, jwt_status = 'valid' WHERE mobile_number =%s",
            #         (access_token, mobile_number)
            #     ) 
        else:
            db_cursor.execute(
                "INSERT INTO user_jwt(mobile_number,jwt_token,jwt_status) VALUES(%s,%s,'valid')",
                (mobile_number, access_token)
            )

        if data.device_token:
            db_cursor.execute("""
                INSERT INTO user_devices (mobile_number, device_token)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE device_token = %s
            """, (mobile_number, data.device_token, data.device_token))

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