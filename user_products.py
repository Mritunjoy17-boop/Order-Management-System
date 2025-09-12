from fastapi import FastAPI,HTTPException,Depends,status
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from fastapi.exception_handlers import RequestValidationError
from pydantic import BaseModel
import mysql.connector

app = FastAPI()

#db connection
def connect_db():
    conn = mysql.connector.connect(
        host = '167.235.199.142',
        user = 'root',
        password = 'Orders@159!',
        database = 'orders_db'
    )

    try:
        yield conn
    finally:
        conn.close()

#pydantic models
class UserproductsRequest(BaseModel):
    mobile_number : str

class UserproductsResponse(BaseModel):
    message : dict

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail}
    )

@app.post("/user_products", response_model = UserproductsResponse)
async def get_categories(data : UserproductsRequest, db=Depends(connect_db)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT product_code FROM user_products WHERE user_mobile =%s",
        (data.mobile_number,)
    )
    query_data = db_cursor.fetchall()
    if query_data:
        if isinstance(query_data, list) and len(query_data) > 0:
            product_code_list = []
            for temp_dict in query_data:
                if temp_dict.get('product_code','') != '':
                    product_code_list.append(temp_dict['product_code'])

            success_message = "Product codes found"
            db_cursor.close()

            return_dict = {
                "userproducts_data" : {
                    "product_code" : product_code_list
                }
            }

            json_response = {
                "msg": success_message,"status":"Success","data":return_dict
            }

            return {"message": json_response}
    else:
        db_cursor.close()
        failure_msg = "Invalid mobile number"
        failure_response = {
            "msg": failure_msg,"status":"Failure","data":{}
        }
        return {"message": failure_response}