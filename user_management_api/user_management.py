import os
import sys
from pydantic import BaseModel
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI,HTTPException,Depends,status,Header
from fastapi.exceptions import RequestValidationError
from validate_token import validate_token,get_tokens
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from db_config import connect_db

app = FastAPI()

#pydantic models

class StandardResponse(BaseModel):
    message : dict
class CreateUserRequest(BaseModel):
    user_name: str
    mobile_number: str
    user_type: str
    password: str
    
@app.get("/", response_model=StandardResponse)
async def get_users(db=Depends(connect_db), token=Depends(get_tokens)):
    validate_token(db, token)

    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute("SELECT user_name, mobile_number, user_type FROM users")

    user_data = db_cursor.fetchall()
    if user_data:
        data = []
        for user_dict in user_data:
            data.append(user_dict)
    else:
        data = []
        
        
    return_dict = {
        "number_of_users": len(data),
        "user_data": data
    }
    json_response = {
        "msg": "User List Fetch Successfully","status":"Success","data":return_dict
    }
    db_cursor.close()

    return {
        "message": json_response
    }
        
        
@app.post("/create", response_model=StandardResponse)
async def create_user(
    data: CreateUserRequest,
    db=Depends(connect_db),
    token: str = Depends(get_tokens)
):
    
    try:
        result = validate_token(db, token)
        user_mobile = result["mobile_number"]
        is_admin = result.get("user_type") == "Administrator"
        
        cursor = db.cursor()
        if not is_admin:
            cursor.close()
            raise HTTPException(status_code=400, detail="Only Administrators can create Users.")


        cursor.execute("""
            INSERT INTO users (
                user_name, mobile_number, user_type, password
            ) VALUES (%s, %s, %s, %s)
        """, (
            data.user_name,
            data.mobile_number,
            data.user_type,
            data.password
        ))
        
        
            
        db.commit()
        cursor.close()
        return {
            "message": {
                "msg": "Users created successfully",
                "status": "Success",
                "data": {}
            }
        }
    except Exception as e:
        db.rollback()
        raise e
    