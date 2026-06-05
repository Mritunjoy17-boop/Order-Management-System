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




class EachFulfillmentRequest(BaseModel):
    order_id: int
    

class StandardResponse(BaseModel):
    message : dict


@app.post("/fulfillment-list", response_model=StandardResponse)
async def get_fulfillment_list(data: EachFulfillmentRequest,
                              db=Depends(connect_db),
                              token=Depends(get_tokens)):

    validate_token(db, token)

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            f.fulfillment_id,
            f.note,
            f.fulfillment_type,
            f.status_color,
            f.note,
            f.action_by_name,
            f.created_at
        FROM order_fulfillments f
        WHERE f.order_id = %s
        ORDER BY f.created_at ASC
    """, (data.order_id,))

    fulfillments = cursor.fetchall()

    final_data = []

    for f in fulfillments:
        cursor.execute("""
            SELECT 
                product_code,
                product_name,
                fulfilled_quantity
            FROM order_fulfillment_items
            WHERE fulfillment_id = %s
        """, (f["fulfillment_id"],))

        items = cursor.fetchall()

        final_data.append({
            "fulfillment_id": f["fulfillment_id"],
            "fulfillment_type": f["fulfillment_type"],
            "note": f["note"],
            "created_by": f["action_by_name"],
            "created_at": f["created_at"],
            "status_color": f["status_color"],
            "items": items
        })



    cursor.close()

    return {
        "message": {
            "msg": "Fulfillment history fetched",
            "status": "Success",
            "data": {
                "fulfillments": final_data
            }
        }
    }