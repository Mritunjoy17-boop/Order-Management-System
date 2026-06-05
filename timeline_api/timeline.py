import os
import sys
from pydantic import BaseModel
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI,HTTPException,Depends,status,Header,File, UploadFile,Form
from fastapi.exceptions import RequestValidationError
from validate_token import validate_token,get_tokens
import uuid
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from db_config import connect_db

app = FastAPI()


class AddNoteRequest(BaseModel):
    order_id: int
    note: str
    images: list[UploadFile] = File(None)

class EachTimelineRequest(BaseModel):
    order_id: int
    

class StandardResponse(BaseModel):
    message : dict


@app.post("/timeline-list", response_model=StandardResponse)
async def get_timeline_list(data: EachTimelineRequest,
                              db=Depends(connect_db),
                              token=Depends(get_tokens)):

    validate_token(db, token)

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            timeline_id,
            action_type,
            message,
            note,
            action_by_name,
            created_at
        FROM order_timeline
        WHERE order_id = %s
        ORDER BY created_at ASC
    """, (data.order_id,))

    timeline = cursor.fetchall()

    final_data = []

    for t in timeline:
        cursor.execute("""
            SELECT image_url
            FROM order_timeline_images
            WHERE timeline_id = %s
        """, (t["timeline_id"],))

        images = cursor.fetchall()

        # image_list = [img["image_url"] for img in images]
        
        BASE_URL = "http://orders.soni.in:8000"  # change in prod
        
        image_list = [
            f"{BASE_URL}/{img['image_url']}"
            for img in images
        ]

        final_data.append({
            "action_type": t["action_type"],
            "message": t["message"],
            "note": t["note"],
            "action_by_name": t["action_by_name"],
            "created_at": t["created_at"],
            "images": image_list
        })

    cursor.close()

    return {
        "message": {
            "msg": "Timeline fetched",
            "status": "Success",
            "data": {
                "timeline": final_data
            }
        }
    }


@app.post("/add-note", response_model=StandardResponse)
async def add_note(order_id: int = Form(...),
                note: str = Form(...),
                images: list[UploadFile] = File(None),
                db=Depends(connect_db),
                token=Depends(get_tokens)):

    result = validate_token(db, token)
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT order_id, order_status FROM orders
        WHERE order_id = %s
    """, (order_id,))

    order = cursor.fetchone()

    if not order:
        cursor.close()
        raise HTTPException(status_code=404, detail="Order not found")

    # if order_status == "completed":
    #     raise HTTPException(status_code=404, detail="Note cannot be added")

    # Insert timeline note
    cursor.execute("""
        INSERT INTO order_timeline
        (order_id, action_type, message, note, action_by_mobile, action_by_name)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        order_id,
        "Note Added",
        "Note Added",
        note,
        result["mobile_number"],
        result["user_name"]
    ))

    timeline_id = cursor.lastrowid

    # ✅ Save images locally
    upload_dir = "uploads/timeline"
    os.makedirs(upload_dir, exist_ok=True)
    print("Images to upload:", images)
    if images:
        for image in images:
            file_ext = image.filename.split(".")[-1]
            file_name = f"{uuid.uuid4()}.{file_ext}"
            file_path = os.path.join(upload_dir, file_name)

            with open(file_path, "wb") as f:
                f.write(await image.read())

            # Save path in DB
            cursor.execute("""
                INSERT INTO order_timeline_images
                (timeline_id, image_url)
                VALUES (%s, %s)
            """, (timeline_id, file_path))

    db.commit()
    cursor.close()

    return {
        "message": {
            "msg": "Note added successfully",
            "status": "Success"
        }
    }