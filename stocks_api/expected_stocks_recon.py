import os
import sys
from datetime import datetime
from pydantic import BaseModel
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI,HTTPException,Depends,status,Header
from fastapi.exceptions import RequestValidationError

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from db_config import connect_db

app = FastAPI()

#pydantic models
class StocksReconcilationRequest(BaseModel):
    godown_id : str
    category_id : str

class StocksReconcilationResponse(BaseModel):
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

@app.post("/", response_model=StocksReconcilationResponse)
async def expected_stocks_reconcilation(data: StocksReconcilationRequest, db=Depends(connect_db), token : str = Depends(get_tokens)):
    db_cursor = db.cursor(dictionary=True)
    db_cursor.execute(
        "SELECT jwt_status FROM user_jwt WHERE jwt_token =%s",
        (token,)
    )
    token_query = db_cursor.fetchone()
    if token_query and token_query['jwt_status'] == 'valid':
        godown_id = data.godown_id
        category_id = data.category_id

        #inward query
        db_cursor.execute(
            "SELECT prod.product_name, prod.product_code, COUNT(sm.record_id) AS product_count FROM stock_movement sm INNER JOIN products prod ON sm.product_code = prod.product_code INNER JOIN category cat ON prod.product_category = cat.category_id WHERE sm.godown_id =%s AND sm.movement_type = 'inward' AND cat.category_id =%s GROUP BY prod.product_code, prod.product_name",
            (godown_id,category_id)
        )
        inward_reconcilation_data = db_cursor.fetchall()
        print(inward_reconcilation_data)

        #outward query
        db_cursor.execute(
            "SELECT prod.product_name, prod.product_code, COUNT(sm.record_id) AS product_count FROM stock_movement sm INNER JOIN products prod ON sm.product_code = prod.product_code INNER JOIN category cat ON prod.product_category = cat.category_id WHERE sm.godown_id =%s AND sm.movement_type = 'outward' AND cat.category_id =%s GROUP BY prod.product_code, prod.product_name",
            (godown_id,category_id)
        )
        outward_reconcilation_data = db_cursor.fetchall()
        print(outward_reconcilation_data)

        expected_data_list = []
        if inward_reconcilation_data and outward_reconcilation_data:
            product_inward_dict = {}
            for inward_data in inward_reconcilation_data:
                product_inward_dict[inward_data['product_code']] = inward_data

            product_outward_dict = {}
            for outward_data in outward_reconcilation_data:
                product_outward_dict[outward_data['product_code']] = outward_data

            all_keys = product_inward_dict.keys() | product_outward_dict.keys()

            for key in all_keys:
                if key in product_inward_dict and key in product_outward_dict:
                    product = product_inward_dict[key].copy()
                    product['product_count'] = product_inward_dict[key]['product_count'] - product_outward_dict[key]['product_count'] 
                    expected_data_list.append(product)
                elif key in product_inward_dict:
                    expected_data_list.append(product_inward_dict[key].copy())
                else:
                    expected_data_list.append(product_outward_dict[key].copy())
        elif inward_reconcilation_data:
            expected_data_list = inward_reconcilation_data
        elif outward_reconcilation_data:
            expected_data_list = outward_reconcilation_data
            
        if expected_data_list:
            success_message = f"Expected data of stocks reconcilation found successfully"
            db_cursor.close()

            return_dict = {
                "expected_reconcilation_data" : expected_data_list
            }

            json_response = {
                "msg": success_message,"status":"Success","data":return_dict
            }

            return {"message": json_response}
        else:
            db_cursor.close()
            failure_msg = "No expected data found for reconcilation"
            failure_response = {
                "msg": failure_msg,"status":"Failure","data":{}
            }
            return {"message": failure_response}
    else:
        db_cursor.close()
        failure_msg = "Token not valid, login again"
        failure_response = {
            "msg": failure_msg,"status":"Failure","data":{}
        }
        return {"message": failure_response}