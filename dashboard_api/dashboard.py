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
async def get_dashboard(db=Depends(connect_db),
                        token=Depends(get_tokens)):

    result = validate_token(db, token)

    user_type = result["user_type"]
    mobile = result["mobile_number"]

    cursor = db.cursor(dictionary=True)

    if user_type == "Administrator":
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT COUNT(*) FROM products) as total_products,
                (SELECT SUM(total_amount) FROM orders) as total_revenue
        """)

        data = cursor.fetchone()

        response = {
            "message": "Admin dashboard data fetched",
            "total_users": data["total_users"] or 0,
            "total_products": data["total_products"] or 0,
            "total_revenue": float(data["total_revenue"] or 0),
            "pending_alerts": 0
        }

    # =========================
    # ✅ SALES AGENT DASHBOARD
    # =========================
    elif user_type == "sales-agent":

        cursor.execute("""
            SELECT 
                COUNT(*) as total_orders,
                COUNT(CASE 
                    WHEN order_status = 'Pending' THEN 1 
                END) as pending_orders,
                SUM(total_amount) as total_revenue
            FROM orders
            WHERE sales_agent_mobile = %s
        """, (mobile,))

        order_stats = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*) as total_customers
            FROM customers
            WHERE sales_agent_mobile = %s
            AND is_active = 1
        """, (mobile,))

        customer_stats = cursor.fetchone()

        response = {
            "message": "Sales agent dashboard data fetched",
            "orders": order_stats["total_orders"] or 0,
            "pending_orders": order_stats["pending_orders"] or 0,
            "revenue": float(order_stats["total_revenue"] or 0),
            "active_clients": customer_stats["total_customers"] or 0
        }

    
    elif user_type == "warehouse-manager":

        cursor.execute("""
            SELECT 
                COUNT(CASE 
                    WHEN o.order_status = 'Pending' THEN 1 
                END) as pending_acceptance,

                COUNT(CASE 
                    WHEN o.order_status = 'Partial' THEN 1 
                END) as partial_fulfilled,

                COUNT(CASE
                    WHEN o.order_status IN ('Pending','Accepted','Partial')
                    THEN 1
                END) as in_progress,

                COUNT(CASE 
                    WHEN o.order_status = 'Completed' THEN 1 
                END) as completed_orders

            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE c.godown_id IN (
                SELECT godown_id
                FROM user_godowns
                WHERE mobile_number = %s
            )
        """, (mobile,))

        stats = cursor.fetchone()

        response = {
            "message": "Warehouse manager dashboard data fetched",
            "pending_acceptance": stats["pending_acceptance"] or 0,
            "partial_fulfilled": stats["partial_fulfilled"] or 0,
            "in_progress": stats["in_progress"] or 0,
            "completed": stats["completed_orders"] or 0
        }
        
    elif user_type == "contributor":
        cursor.execute("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_revenue
            FROM orders
        """)

        order_stats = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*) as active_customers
            FROM customers
            WHERE is_active = 1
        """)

        customer_stats = cursor.fetchone()

        response = {
            "message": "Contributor dashboard data fetched",
            "total_orders": order_stats["total_orders"] or 0,
            "total_revenue": float(order_stats["total_revenue"] or 0),
            "active_customers": customer_stats["active_customers"] or 0
        }

    else:
        cursor.close()
        raise HTTPException(status_code=403, detail="Invalid user role")

    cursor.close()

    return {
        "message": {
            "msg": "Dashboard data fetched",
            "status": "Success",
            "data": {"dashboard_data": response}
        }
    }
    