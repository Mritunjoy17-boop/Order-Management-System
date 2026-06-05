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



class StandardResponse(BaseModel):
    message : dict


@app.get("/", response_model=StandardResponse)
async def get_masters_count(db=Depends(connect_db),
                        token=Depends(get_tokens)):

    result = validate_token(db, token)

    user_type = result["user_type"]
    mobile = result["mobile_number"]

    cursor = db.cursor(dictionary=True)

    if user_type == "Administrator":

        cursor.execute("""
            SELECT 
                u.total_users,
                u.total_roles,
                p.total_products,
                r.total_regions
            FROM 
                (SELECT COUNT(*) AS total_users, COUNT(DISTINCT user_type) AS total_roles FROM users) u,
                (SELECT COUNT(*) AS total_products FROM products) p,
                (SELECT COUNT(*) AS total_regions FROM regions) r
        """)

        data = cursor.fetchone()

        response = {
            "users": data["total_users"] or 0,
            "roles": data["total_roles"] or 0,
            "products": data["total_products"] or 0,
            "regions": data["total_regions"] or 0
        }


    else:
        cursor.close()
        raise HTTPException(status_code=403, detail="Invalid user role")

    cursor.close()

    return {
        "message": {
            "msg": "Master data fetched",
            "status": "Success",
            "data": {"master_data": response}
        }
    }
    