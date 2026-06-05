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


class CreateCustomerRequest(BaseModel):
    business_name: str
    contact_person_name: str
    godown_id: str
    phone_number: str
    city: str
    region_id: int
    

    gstin: str | None = None
    address: str | None = None
    email: str | None = None
    pin_code: str | None = None
    whatsapp_number: str | None = None
    alternate_phone: str | None = None
    sales_agents: list[str] | None = None
    
class EachCustomerRequest(BaseModel):
    customer_id: int
    

class StandardResponse(BaseModel):
    message : dict


@app.post("/create", response_model=StandardResponse)
async def create_customer(
    data: CreateCustomerRequest,
    db=Depends(connect_db),
    token: str = Depends(get_tokens)
):
    
    try:
        result = validate_token(db, token)
        user_mobile = result["mobile_number"]
        is_admin = result.get("user_type") == "Administrator"
        
        cursor = db.cursor(dictionary=True)
        if is_admin and not data.sales_agents:
            cursor.close()
            raise HTTPException(status_code=400, detail="Sales agents required for admin")


        cursor.execute("""
            INSERT INTO customers (
                business_name, contact_person_name, godown_id,
                phone_number, city, region_id,
                gstin, address, email, pin_code,
                whatsapp_number, alternate_phone,sales_agent_mobile
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data.business_name,
            data.contact_person_name,
            data.godown_id,
            data.phone_number,
            data.city,
            data.region_id,
            data.gstin,
            data.address,
            data.email,
            data.pin_code,
            data.whatsapp_number,
            data.alternate_phone,
            user_mobile
        ))
        
        customer_id = cursor.lastrowid

        if not is_admin:
            cursor.execute("""
                INSERT INTO customer_sales_agents (customer_id, sales_agent_mobile, assigned_by)
                VALUES (%s, %s, %s)
            """, (customer_id, user_mobile, user_mobile))
        else:
            # print("Sales agents to assign:", data.sales_agents)
            # cursor.execute("""
            #     SELECT mobile_number FROM users
            #     WHERE mobile_number IN %s
            # """, (tuple(data.sales_agents),))

            # valid_agents = {row[0] for row in cursor.fetchall()}
            for agent in data.sales_agents:
                # if agent not in valid_agents:
                #     raise HTTPException(status_code=400, detail=f"Invalid agent {agent}")
                cursor.execute("""
                    INSERT INTO customer_sales_agents 
                    (customer_id, sales_agent_mobile, assigned_by)
                    VALUES (%s, %s, %s)
                """, (customer_id, agent, user_mobile))
                
        cursor.execute("""
            SELECT 
                c.customer_id,
                c.business_name,
                c.contact_person_name,
                c.phone_number,
                c.city,
                c.godown_id,
                c.region_id,
                r.region_name,
                c.gstin,
                c.address,
                c.email,
                c.pin_code,
                c.whatsapp_number,
                c.alternate_phone,
                c.sales_agent_mobile,
                c.created_at
            FROM customers c
            LEFT JOIN regions r 
                ON c.region_id = r.region_id
            WHERE c.customer_id = %s
        """, (customer_id,))

        customer_data = cursor.fetchone()
            
        db.commit()
        cursor.close()
        return {
            "message": {
                "msg": "Customer created successfully",
                "status": "Success",
                "data": {
                    "customer_data": customer_data
                }
            }
        }
    except Exception as e:
        db.rollback()
        raise e
    
@app.get("/list", response_model=StandardResponse)
async def get_customers(
    db=Depends(connect_db),
    token: str = Depends(get_tokens)
):
    result = validate_token(db, token)
    is_admin = result.get("user_type") == "Administrator"
    
    

    cursor = db.cursor(dictionary=True)
    
    if is_admin:
        cursor.execute("""
            SELECT c.customer_id, c.business_name, c.phone_number,
                c.city, r.region_name,r.region_id,
                COUNT(o.order_id) as total_orders
            FROM customers c
            LEFT JOIN orders o ON c.customer_id = o.customer_id
            LEFT JOIN regions r ON c.region_id = r.region_id
            WHERE c.is_active = 1
            GROUP BY c.customer_id
        """)
    else:
        sales_agent_mobile = result["mobile_number"]
        cursor.execute("""
            SELECT c.customer_id, c.business_name, c.phone_number,
                c.city, r.region_name, r.region_id,
                COUNT(o.order_id) as total_orders
            FROM customers c

            JOIN customer_sales_agents csa 
                ON c.customer_id = csa.customer_id

            LEFT JOIN orders o 
                ON c.customer_id = o.customer_id
                AND o.sales_agent_mobile = %s

            LEFT JOIN regions r 
                ON c.region_id = r.region_id

            WHERE c.is_active = 1
            AND csa.sales_agent_mobile = %s

            GROUP BY c.customer_id
        """, (sales_agent_mobile, sales_agent_mobile))

    # cursor.execute("""
    #     SELECT c.customer_id, c.business_name, c.phone_number,
    #         c.city, r.region_name,
    #         COUNT(o.order_id) as total_orders
    #     FROM customers c
    #     LEFT JOIN orders o 
    #         ON c.customer_id = o.customer_id
    #         AND o.sales_agent_mobile = %s   -- 🔥 IMPORTANT
    #     LEFT JOIN regions r ON c.region_id = r.region_id
    #     WHERE c.is_active = 1
    #     AND c.sales_agent_mobile = %s       -- 🔥 IMPORTANT
    #     GROUP BY c.customer_id
    # """, (sales_agent_mobile, sales_agent_mobile))

    data = cursor.fetchall()
    return_dict = {
        "customer_data": data
    }
    cursor.close()

    return {
        "message": {
            "msg": "Customer list fetched",
            "status": "Success",
            "data": return_dict
        }
    }
    
@app.post("/detail", response_model=StandardResponse)
async def get_customer_detail(data: EachCustomerRequest,
                              db=Depends(connect_db),
                              token=Depends(get_tokens)):

    result = validate_token(db, token)
    sales_agent_mobile = result["mobile_number"]
    
    is_admin = result.get("user_type") == "Administrator"


    cursor = db.cursor(dictionary=True)
    
    if data.customer_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid customer ID")
    
    if is_admin:
        cursor.execute("""
            SELECT c.*, r.region_name
            FROM customers c
            LEFT JOIN regions r ON c.region_id = r.region_id
            WHERE c.customer_id = %s
        """, (data.customer_id,))
    else:
        cursor.execute("""
        SELECT c.*, r.region_name
        FROM customers c
        LEFT JOIN regions r ON c.region_id = r.region_id
        JOIN customer_sales_agents csa 
            ON c.customer_id = csa.customer_id
        WHERE c.customer_id = %s
        AND csa.sales_agent_mobile = %s
     """, (data.customer_id, sales_agent_mobile))

    # cursor.execute("""
    #     SELECT c.*, r.region_name
    #     FROM customers c
    #     LEFT JOIN regions r ON c.region_id = r.region_id
    #     WHERE c.customer_id = %s
    #     AND c.sales_agent_mobile = %s
    # """, (data.customer_id, sales_agent_mobile))

    customer_data = cursor.fetchone()

    if not customer_data:
        cursor.close()
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if is_admin:
        cursor.execute("""
             SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_revenue,
                COUNT(CASE
                    WHEN order_status IN ('Pending','Accepted','Partial')
                    THEN 1
                END) as active_orders
             FROM orders
             WHERE customer_id = %s
         """, (data.customer_id,))
    else:
         cursor.execute("""
             SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_revenue,
                COUNT(CASE
                    WHEN order_status IN ('Pending','Accepted','Partial')
                    THEN 1
                END) as active_orders
             FROM orders
             WHERE customer_id = %s
             AND sales_agent_mobile = %s
         """, (data.customer_id, sales_agent_mobile))
         
    # cursor.execute("""
    #          SELECT COUNT(*) as total_orders,
    #                 SUM(total_amount) as total_revenue
    #          FROM orders
    #          WHERE customer_id = %s
    #          AND sales_agent_mobile = %s
    #      """, (data.customer_id, sales_agent_mobile))
        
    stats = cursor.fetchone()

    if is_admin:
        cursor.execute("""
            SELECT 
                o.order_id,
                o.order_number,
                o.total_items,
                o.total_quantity,
                o.total_fulfilled,
                o.order_status,
                o.total_amount,
                o.created_at,
                c.business_name
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.customer_id = %s
            ORDER BY o.created_at DESC
        """, (data.customer_id,))
    else:
        cursor.execute("""
            SELECT 
                o.order_id,
                o.order_number,
                o.total_items,
                o.total_quantity,
                o.total_fulfilled,
                o.order_status,
                o.total_amount,
                o.created_at,
                c.business_name
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN customer_sales_agents csa 
                ON o.customer_id = csa.customer_id

            WHERE o.customer_id = %s
            AND csa.sales_agent_mobile = %s
            ORDER BY o.created_at DESC
        """, (data.customer_id, sales_agent_mobile))

    orders = cursor.fetchall()
    cursor.close()

    formatted_orders = []

    for o in orders:
        formatted_orders.append({
            "order_id": o["order_id"],
            "order_number": o["order_number"],
            "total_items": o["total_items"],
            "total_quantity": o["total_quantity"],
            "total_fulfilled": o["total_fulfilled"],
            "order_status": o["order_status"],
            "total_amount": str(o["total_amount"]),  
            "created_at": o["created_at"],
            "business_name": o["business_name"]
        })
    
    
    response = {
        "customer": customer_data,
        "total_orders": stats["total_orders"] or 0,
        "total_revenue": float(stats["total_revenue"] or 0),
        "active_orders": stats["active_orders"] or 0
    }

    return_dict = {
        "customer_data" : response,
        "orders": formatted_orders
    }

    return {
        "message": {
            "msg": "Customer details fetched",
            "status": "Success",
            "data": return_dict
        }
    }
    
    
# @app.get("/list")
# async def get_customers(db=Depends(connect_db),
#                         token=Depends(get_tokens)):

#     validate_token(db, token)
#     cursor = db.cursor(dictionary=True)

#     cursor.execute("""
#         SELECT c.customer_id,
#                c.business_name,
#                c.phone_number,
#                COUNT(o.order_id) as total_orders
#         FROM customers c
#         LEFT JOIN orders o ON c.customer_id = o.customer_id
#         WHERE c.is_active = 1
#         GROUP BY c.customer_id
#     """)

#     data = cursor.fetchall()
#     cursor.close()

#     return {
#         "message": {
#             "msg": "Customers fetched",
#             "status": "Success",
#             "data": data
#         }
#     }



# @app.get("/detail/{customer_id}")
# async def get_customer_detail(customer_id: int,
#                               db=Depends(connect_db),
#                               token=Depends(get_tokens)):

#     validate_token(db, token)
#     cursor = db.cursor(dictionary=True)

#     # Customer info
#     cursor.execute("""
#         SELECT *
#         FROM customers
#         WHERE customer_id = %s
#     """, (customer_id,))
#     customer = cursor.fetchone()

#     if not customer:
#         raise HTTPException(status_code=404, detail="Customer not found")

#     # Orders summary
#     cursor.execute("""
#         SELECT COUNT(*) as total_orders,
#                SUM(total_amount) as total_revenue
#         FROM orders
#         WHERE customer_id = %s
#     """, (customer_id,))
    
#     stats = cursor.fetchone()
#     cursor.close()

#     response = {
#         "customer": customer,
#         "total_orders": stats["total_orders"] or 0,
#         "total_revenue": float(stats["total_revenue"] or 0)
#     }

#     return {
#         "message": {
#             "msg": "Customer details fetched",
#             "status": "Success",
#             "data": response
#         }
#     }