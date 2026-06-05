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


class StandardResponse(BaseModel):
    message : dict



@app.get("/pending-items-summary", response_model=StandardResponse)
async def get_items_summary(db=Depends(connect_db),
                            token=Depends(get_tokens)):

    result = validate_token(db, token)

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            p.product_code,
            p.product_name,

            SUM(CASE 
                WHEN o.order_status = 'Pending' 
                THEN oi.quantity ELSE 0 
            END) AS pending,

            SUM(CASE 
                WHEN o.order_status = 'Accepted' 
                THEN oi.quantity ELSE 0 
            END) AS accepted,

            SUM(CASE 
                WHEN o.order_status = 'Partial' 
                THEN oi.fulfilled ELSE 0 
            END) AS partial

        FROM products p

        LEFT JOIN order_items oi 
            ON p.product_code = oi.product_code

        LEFT JOIN orders o 
            ON oi.order_id = o.order_id

        GROUP BY p.product_code, p.product_name

        HAVING 
            pending > 0 
            OR accepted > 0 
            OR partial > 0
    """)

    data = cursor.fetchall()
    cursor.close()

    return {
        "message": {
            "msg": "Items summary fetched",
            "status": "Success",
            "data": {
                "items": data
            }
        }
    }
    
    
@app.get("/sales-agent-performance", response_model=StandardResponse)
async def sales_agent_performance(db=Depends(connect_db),
                                  token=Depends(get_tokens)):

    validate_token(db, token)

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            u.mobile_number,
            u.user_name,
            r.region_name,
            COUNT(CASE 
                WHEN o.order_status IN ('Pending','Accepted','Partial') 
                THEN 1 
            END) AS active_orders,

            COUNT(o.order_id) AS total_orders,
            COALESCE(SUM(o.total_amount), 0) AS total_revenue

        FROM users u

        LEFT JOIN orders o 
            ON u.mobile_number = o.sales_agent_mobile

        LEFT JOIN customers c
            ON o.customer_id = c.customer_id
        
        LEFT JOIN regions r
            ON c.region_id = r.region_id

        WHERE u.user_type = 'sales-agent'

        GROUP BY u.mobile_number, u.user_name, r.region_name

    """)

    data = cursor.fetchall()
    cursor.close()

    return {
        "message": {
            "msg": "Sales agent performance fetched",
            "status": "Success",
            "data": {
                "agents": data
            }
        }
    }
    
    
@app.get("/customer-aging", response_model=StandardResponse)
async def customer_aging(db=Depends(connect_db),
                         token=Depends(get_tokens)):

    validate_token(db, token)

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            c.customer_id,
            c.business_name,
            r.region_name,

            COUNT(o.order_id) AS open_orders,

            CONCAT(
                FLOOR(TIMESTAMPDIFF(HOUR, MIN(o.created_at), NOW()) / 24),
                'd ',
                MOD(TIMESTAMPDIFF(HOUR, MIN(o.created_at), NOW()), 24),
                'h'
            ) AS waiting_days

        FROM customers c

        JOIN orders o 
            ON c.customer_id = o.customer_id

        LEFT JOIN regions r 
            ON c.region_id = r.region_id

        WHERE o.order_status IN ('Pending','Partial')

        GROUP BY c.customer_id, c.business_name, r.region_name

        ORDER BY 
            TIMESTAMPDIFF(HOUR, MIN(o.created_at), NOW()) DESC
    """)

    data = cursor.fetchall()
    cursor.close()

    return {
        "message": {
            "msg": "Customer Aging dashboard fetched",
            "status": "Success",
            "data": {
                "customers": data
            }
        }
    }
    
@app.get("/warehouse-performance", response_model=StandardResponse)
async def warehouse_performance(db=Depends(connect_db),
                                token=Depends(get_tokens)):

    validate_token(db, token)

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            u.mobile_number,
            u.user_name,
            g.godown_name,
            g.godown_id,

            COUNT(DISTINCT CASE 
                WHEN ot.action_type IN ('Accepted', 'Partial') 
                THEN ot.order_id 
            END) AS handled_orders,

            COUNT(DISTINCT CASE 
                WHEN o.order_status = 'Completed'
                AND ot.action_type IN ('Accepted', 'Partial')
                THEN o.order_id 
            END) AS completed_orders,

            CASE 
                WHEN COUNT(DISTINCT CASE 
                    WHEN ot.action_type IN ('Accepted', 'Partial') 
                    THEN ot.order_id 
                END) = 0 THEN 0

                ELSE ROUND(
                    COUNT(DISTINCT CASE 
                        WHEN o.order_status = 'Completed'
                        AND ot.action_type IN ('Accepted', 'Partial')
                        THEN o.order_id 
                    END) * 100.0
                    /
                    COUNT(DISTINCT CASE 
                        WHEN ot.action_type IN ('Accepted', 'Partial') 
                        THEN ot.order_id 
                    END),
                2)
            END AS completion_rate

        FROM users u

        LEFT JOIN order_timeline ot 
            ON u.mobile_number = ot.action_by_mobile

        LEFT JOIN orders o 
            ON ot.order_id = o.order_id
        
         LEFT JOIN user_godowns ug
            ON u.mobile_number = ug.mobile_number

        LEFT JOIN godowns g
            ON ug.godown_id = g.godown_id

        WHERE u.user_type = 'warehouse-manager'

        GROUP BY u.mobile_number, u.user_name, g.godown_name, g.godown_id
    """)

    data = cursor.fetchall()
    cursor.close()

    return {
        "message": {
            "msg": "Warehouse performance fetched",
            "status": "Success",
            "data": {
                "warehouse": data
            }
        }
    }