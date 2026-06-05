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
class CreateRegionRequest(BaseModel):
    region_name: str
    state: str
    
@app.get("/list", response_model=StandardResponse)
async def get_regions(db=Depends(connect_db), token=Depends(get_tokens)):
    validate_token(db, token)

    db_cursor = db.cursor(dictionary=True)
    
    db_cursor.execute("SELECT region_id, region_name as region, state FROM regions")

    region_data = db_cursor.fetchall()
    if region_data:
        data = []
        for region_dict in region_data:
            region_dict["region_name"] = f"{region_dict['region']} - {region_dict['state']}"
            data.append(region_dict)
    else:
        data = []
        
        
    return_dict = {
        "number_of_regions": len(data),
        "region_data": data
    }
    json_response = {
        "msg": "Region List Fetch Successfully","status":"Success","data":return_dict
    }
    db_cursor.close()

    return {
        "message": json_response
    }
        
        
@app.post("/create", response_model=StandardResponse)
async def create_region(
    data: CreateRegionRequest,
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
            raise HTTPException(status_code=400, detail="Only Administrators can create Regions.")


        cursor.execute("""
            INSERT INTO regions (
                region_name, state
            ) VALUES (%s, %s)
        """, (
            data.region_name,
            data.state
        ))
        
        
            
        db.commit()
        cursor.close()
        return {
            "message": {
                "msg": "Regions created successfully",
                "status": "Success",
                "data": {}
            }
        }
    except Exception as e:
        db.rollback()
        raise e
    