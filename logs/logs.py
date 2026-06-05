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

class EachLogRequest(BaseModel):
    log_id: int


@app.get("/list", response_model=StandardResponse)
async def get_logs(
    db=Depends(connect_db),
    token=Depends(get_tokens),

    user_mobile: str = None,
    endpoint: str = None,
    start_date: str = None,
    end_date: str = None,

    page: int = 1,
    limit: int = 20
):

    result = validate_token(db, token)

    if result["user_type"] != "Administrator":
        raise HTTPException(status_code=403, detail="Unauthorized")

    cursor = db.cursor(dictionary=True)

    offset = (page - 1) * limit

    query = """
        SELECT log_id, user_mobile, user_name, user_type,
               endpoint, method,status_message,request_body,
               response_status, ip_address,latitude,longitude,created_at,created_date
        FROM api_logs
        WHERE 1=1
    """

    params = []

    # ✅ Filters
    if user_mobile:
        query += " AND user_mobile = %s"
        params.append(user_mobile)

    if endpoint:
        query += " AND endpoint LIKE %s"
        params.append(f"%{endpoint}%")

    if start_date:
        query += " AND created_date >= %s"
        params.append(start_date)

    if end_date:
        query += " AND created_date <= %s"
        params.append(end_date)

    # ✅ Pagination
    # query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    # params.extend([limit, offset])

    cursor.execute(query, tuple(params))
    logs = cursor.fetchall()

    cursor.close()

    return {
        "message": {
            "msg": "Logs fetched",
            "status": "Success",
            "data": {
                "logs": logs,
                "page": page,
                "limit": limit
            }
        }
    }


@app.post("/detail", response_model=StandardResponse)
async def get_log_detail(data: EachLogRequest,
                         db=Depends(connect_db),
                         token=Depends(get_tokens)):

    result = validate_token(db, token)

    if result["user_type"] != "Administrator":
        raise HTTPException(status_code=403, detail="Unauthorized")

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM api_logs
        WHERE log_id = %s
    """, (data.log_id,))

    log = cursor.fetchone()
    cursor.close()

    return {
        "message": {
            "msg": "Log detail fetched",
            "status": "Success",
            "data": log
        }
    }