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
class LogoutResponse(BaseModel):
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

@app.get("/", response_model=LogoutResponse)
async def user_logout(db=Depends(connect_db), token : str = Depends(get_tokens)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT mobile_number,jwt_status FROM user_jwt WHERE jwt_token =%s",    
        (token,)
    )
    token_query = db_cursor.fetchone()
    if token_query and token_query['jwt_status'] == 'valid':
        db_cursor.execute(
            "UPDATE user_jwt SET jwt_status = 'invalid' WHERE jwt_token =%s",
            (token,)
        )
        db.commit()
        db_cursor.close()

        json_response = {
            "msg": "User logged out successfully","status":"Success","data":{}
        }

        return {"message": json_response}
    else:
        db_cursor.close()
        failure_msg = "Token not valid, login again"
        failure_response = {
            "msg": failure_msg,"status":"Failure","data":{}
        }
        return {"message": failure_response}