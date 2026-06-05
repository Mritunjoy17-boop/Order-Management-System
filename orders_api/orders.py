import os
import sys
from pydantic import BaseModel
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI,HTTPException,Depends,status,Header
from fastapi.exceptions import RequestValidationError
from validate_token import validate_token,get_tokens
from utils.notifications import send_order_notification
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import A4, A6
from reportlab.platypus import PageBreak

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)

from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)

from reportlab.lib.enums import TA_CENTER

from reportlab.lib import colors

from reportlab.lib.units import mm
from datetime import datetime
from utils.order_pdf_helper import build_order_section
import zipfile


current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from db_config import connect_db

app = FastAPI()



class StandardResponse(BaseModel):
    message : dict

class OrderItem(BaseModel):
    product_code: str
    quantity: int


class CreateOrderRequest(BaseModel):
    customer_id: int
    items: list[OrderItem]
    notes: str | None = None
    
class EachOrderRequest(BaseModel):
    order_id: int

class UpdateStatusRequest(BaseModel):
    order_id: int
    status: str  # accepted / rejected
    
class UpdateInvoiceStatusRequest(BaseModel):
    order_id: int
    # invoice_status: str 

class PartialItem(BaseModel):
    product_code: str
    fulfilled: int

class PartialRequest(BaseModel):
    order_id: int
    items: list[PartialItem]
    notes: str | None = None
    
class OrderPDFRequest(BaseModel):
    order_id: int
    
class MultipleOrdersPDFRequest(BaseModel):
    order_ids: list[int]


@app.post("/create")
async def create_order(data: CreateOrderRequest,
                       db=Depends(connect_db),
                       token=Depends(get_tokens)):

    result = validate_token(db, token)
    sales_agent_mobile = result["mobile_number"]
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as count FROM orders")
    count = cursor.fetchone()["count"] + 1
    order_number = f"SB-{1000 + count}"

    total_items = len(data.items)
    total_quantity = 0
    total_amount = 0

    item_data = []

    for item in data.items:

        cursor.execute("""
            SELECT price_per_unit
            FROM products
            WHERE product_code = %s
        """, (item.product_code,))

        product = cursor.fetchone()

        if not product:
            raise HTTPException(status_code=404,
                                detail=f"Product {item.product_code} not found")

        price = product["price_per_unit"]
        item_total = price * item.quantity

        total_quantity += item.quantity
        total_amount += item_total

        item_data.append((item.product_code, item.quantity, price, item_total))

    cursor.execute("""
        INSERT INTO orders (
            order_number, customer_id,
            total_items, total_quantity,
            total_amount, sales_agent_mobile, notes
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        order_number,
        data.customer_id,
        total_items,
        total_quantity,
        total_amount,
        sales_agent_mobile,
        data.notes
    ))

    order_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO order_timeline 
        (order_id, action_type, message, action_by_mobile, action_by_name)
        VALUES (%s, 'Created', 'Order created', %s, %s)
    """, (order_id, sales_agent_mobile, result["user_name"]))

    for item in item_data:
        cursor.execute("""
            INSERT INTO order_items
            (order_id, product_code, quantity, price_per_unit, total_price)
            VALUES (%s,%s,%s,%s,%s)
        """, (order_id, *item))

    cursor.execute("""
        SELECT u.mobile_number
        FROM user_godowns ug
        JOIN users u ON ug.mobile_number = u.mobile_number
        WHERE ug.godown_id = (
            SELECT godown_id FROM customers WHERE customer_id = %s
        )
        AND u.user_type = 'warehouse-manager'
    """, (data.customer_id,))

    warehouse_users = cursor.fetchall()

    mobiles = [u["mobile_number"] for u in warehouse_users]

    if mobiles:
        placeholders = ','.join(['%s'] * len(mobiles))

        query = f"""
            SELECT device_token 
            FROM user_devices
            WHERE mobile_number IN ({placeholders})
        """

        cursor.execute(query, mobiles)
        tokens = [row["device_token"] for row in cursor.fetchall()]
    else:
        tokens = []


    db.commit()
    send_order_notification(
        tokens,
        "New Order",
        f"New order placed for customer {data.customer_id} and the Order number is {order_number}",
        order_id
    )
    cursor.close()

    return {
        "message": {
            "msg": f"Order Created - #{order_number}",
            "status": "Success",
            "data": {
                "order_number": order_number,
                "total_amount": total_amount
            }
        }
    }
    
@app.get("/list", response_model=StandardResponse)
async def get_orders(db=Depends(connect_db),
                     token=Depends(get_tokens)):

    result = validate_token(db, token)
    user_type = result["user_type"]
    mobile = result["mobile_number"]

    cursor = db.cursor(dictionary=True)

    if user_type == "Administrator" or user_type == "contributor":
        cursor.execute("""
            SELECT o.order_id, o.order_number,
                   o.total_items, o.total_quantity, o.total_fulfilled,
                   o.order_status,o.invoice_status, o.total_amount, o.created_at,
                   c.business_name
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            ORDER BY o.created_at DESC
        """)
    elif user_type == "warehouse-manager":
        cursor.execute("""
            SELECT o.order_id, o.order_number,
                   o.total_items, o.total_quantity, o.total_fulfilled,
                   o.order_status,o.invoice_status, o.total_amount, o.created_at,
                   c.business_name
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE c.godown_id IN (
                SELECT godown_id 
                FROM user_godowns 
                WHERE mobile_number = %s
            )
            ORDER BY o.created_at DESC
        """, (mobile,))
    elif user_type == "sales-agent" or user_type == "sales-manager":
        cursor.execute("""
            SELECT o.order_id, o.order_number,
                o.total_items, o.total_quantity, o.total_fulfilled,
                o.order_status,o.invoice_status, o.total_amount, o.created_at,
                c.business_name
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN customer_sales_agents csa 
                ON c.customer_id = csa.customer_id
            WHERE csa.sales_agent_mobile = %s
            ORDER BY o.created_at DESC
        """, (mobile,))

    # cursor.execute("""
    #     SELECT o.order_id, o.order_number,
    #            o.total_items, o.total_quantity,
    #            o.order_status,o.total_amount, o.created_at,
    #            c.business_name
    #     FROM orders o
    #     JOIN customers c ON o.customer_id = c.customer_id
    #     ORDER BY o.created_at DESC
    # """)

    data = cursor.fetchall()
    return_dict = {
        "order_data": data
    }
    cursor.close()

    return {
        "message": {
            "msg": "Orders fetched",
            "status": "Success",
            "data": return_dict
        }
    }
    
@app.post("/detail", response_model=StandardResponse)
async def get_order(data: EachOrderRequest,
                    db=Depends(connect_db),
                    token=Depends(get_tokens)):

    result = validate_token(db, token)
    is_admin = result["user_type"] == "Administrator" or result["user_type"] == "warehouse-manager" or result["user_type"] == "contributor"

    if data.order_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    cursor = db.cursor(dictionary=True)
    
    # if is_admin:
    #     cursor.execute("""
    #         SELECT o.order_id, o.order_number,
    #                o.total_items, o.total_quantity,o.total_fulfilled,
    #                o.order_status,
    #                o.total_amount, o.created_at,
    #                c.customer_id, c.business_name,
    #                r.region_name,
    #                u.user_name AS sales_agent_name,
    #                o.sales_agent_mobile
    #         FROM orders o
    #         JOIN customers c ON o.customer_id = c.customer_id
    #         LEFT JOIN regions r ON c.region_id = r.region_id
    #         LEFT JOIN users u ON o.sales_agent_mobile = u.mobile_number
    #         WHERE o.order_id = %s
    #     """, (data.order_id,))
    # else:
    #     sales_agent_mobile = result["mobile_number"]
    #     cursor.execute("""
    #         SELECT o.order_id, o.order_number,
    #                o.total_items, o.total_quantity, o.total_fulfilled,
    #                o.order_status, o.total_amount, o.created_at,
    #                o.total_amount, o.created_at,
    #                c.customer_id, c.business_name,
    #                r.region_name,
    #                u.user_name AS sales_agent_name,
    #                o.sales_agent_mobile
    #         FROM orders o
    #         JOIN customers c ON o.customer_id = c.customer_id
    #         LEFT JOIN regions r ON c.region_id = r.region_id
    #         LEFT JOIN users u ON o.sales_agent_mobile = u.mobile_number
    #         WHERE o.order_id = %s
    #         AND o.sales_agent_mobile = %s
    #     """, (data.order_id, sales_agent_mobile))
    if is_admin:
        cursor.execute("""
            SELECT o.order_id, o.order_number,
                    o.total_items, o.total_quantity,o.total_fulfilled,
                    o.order_status, o.invoice_status,
                    o.total_amount, o.created_at,
                    c.customer_id, c.business_name,c.godown_id,
                    r.region_name,
                    u.user_name AS sales_agent_name,
                    o.sales_agent_mobile,
                    u1.user_name AS processed_by_name,
                    u1.mobile_number AS processed_by_mobile
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN regions r ON c.region_id = r.region_id
            JOIN customer_sales_agents csa 
                ON c.customer_id = csa.customer_id
            LEFT JOIN users u ON csa.sales_agent_mobile = u.mobile_number
            LEFT JOIN users u1 ON o.processed_by = u1.mobile_number
            WHERE o.order_id = %s
        """, (data.order_id,))
    else:
        cursor.execute("""
            SELECT o.order_id, o.order_number,
                    o.total_items, o.total_quantity,o.total_fulfilled,
                    o.order_status, o.invoice_status,
                    o.total_amount, o.created_at,
                    c.customer_id, c.business_name,c.godown_id,
                    r.region_name,
                    u.user_name AS sales_agent_name,
                    o.sales_agent_mobile,
                    u1.user_name AS processed_by_name,
                    u1.mobile_number AS processed_by_mobile
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN regions r ON c.region_id = r.region_id
            JOIN customer_sales_agents csa 
                ON c.customer_id = csa.customer_id
            LEFT JOIN users u ON csa.sales_agent_mobile = u.mobile_number
            LEFT JOIN users u1 ON o.processed_by = u1.mobile_number
            WHERE o.order_id = %s
            AND csa.sales_agent_mobile = %s
        """, (data.order_id,result["mobile_number"]))

    # cursor.execute("""
    #     SELECT o.order_id, o.order_number,
    #            o.total_items, o.total_quantity,
    #            o.total_amount, o.created_at,
    #            c.customer_id, c.business_name,
    #            r.region_name,
    #            u.user_name AS sales_agent_name,
    #            o.sales_agent_mobile
    #     FROM orders o
    #     JOIN customers c ON o.customer_id = c.customer_id
    #     LEFT JOIN regions r ON c.region_id = r.region_id
    #     LEFT JOIN users u ON o.sales_agent_mobile = u.mobile_number
    #     WHERE o.order_id = %s
    # """, (data.order_id,))

    order = cursor.fetchone()

    if not order:
        cursor.close()
        raise HTTPException(status_code=404, detail="Order not found")

    cursor.execute("""
        SELECT 
            oi.product_code,
            p.product_name,
            c.category_name,
            oi.quantity,
            oi.price_per_unit,oi.fulfilled,
            oi.total_price
        FROM order_items oi
        JOIN products p ON oi.product_code = p.product_code
        LEFT JOIN category c ON p.product_category = c.category_id
        WHERE oi.order_id = %s
    """, (data.order_id,))

    items = cursor.fetchall()
    cursor.close()

    formatted_items = []
    for item in items:
        formatted_items.append({
            "product_name": item["product_name"],
            "product_code": item["product_code"],
            "category": item["category_name"],  
            "quantity": item["quantity"],
            "fulfilled": item["fulfilled"],
            "price_per_unit": float(item["price_per_unit"]),
            "total_price": float(item["total_price"])
        })

    response_data = {
        "order_id": order["order_id"],
        "order_number": order["order_number"],
        "order_status": order["order_status"],
        "invoice_status": order["invoice_status"],
        "created_at": order["created_at"],

        "customer": {
            "customer_id": order["customer_id"],
            "business_name": order["business_name"],
            "godown_id": order["godown_id"],
            "region": order["region_name"]
        },

        "sales_agent": {
            "mobile": order["sales_agent_mobile"],
            "name": order["sales_agent_name"]
        },

        "processed_by": {
            "mobile": order["processed_by_mobile"],
            "name": order["processed_by_name"]
        },

        "summary": {
            "total_items": order["total_items"],
            "total_quantity": order["total_quantity"],
            "total_fulfilled": order["total_fulfilled"],
            "total_amount": float(order["total_amount"])
        },

        "items": formatted_items
    }

    return_dict = {
        "order_data": response_data
    }

    return {
        "message": {
            "msg": "Order fetched",
            "status": "Success",
            "data": return_dict
        }
    }

@app.post("/update-status")
async def update_status(data: UpdateStatusRequest,
                        db=Depends(connect_db),
                        token=Depends(get_tokens)):

    result = validate_token(db, token)

    if result["user_type"] != "warehouse-manager" and result["user_type"] != "Administrator":
        raise HTTPException(status_code=403, detail="Unauthorized")

    if data.status not in ["Accepted", "Rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT order_status
        FROM orders
        WHERE order_id = %s
    """, (data.order_id,))

    order = cursor.fetchone()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["order_status"] != "Pending":
        raise HTTPException(status_code=400,
                            detail="Only pending orders can be updated")

    cursor.execute("""
        UPDATE orders
        SET order_status = %s, processed_by = %s
        WHERE order_id = %s
    """, (data.status, result["mobile_number"], data.order_id))

    cursor.execute("""
        INSERT INTO order_timeline 
        (order_id, action_type, message, action_by_mobile, action_by_name)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        data.order_id,
        data.status,
        f"Order {data.status}",
        result["mobile_number"],
        result["user_name"]
    ))

    db.commit()
    cursor.close()

    return {
        "message": {
            "msg": f"Order {data.status}",
            "status": "Success"
        }
    }

@app.post("/partial-fulfillment")
async def partial_fulfillment(data: PartialRequest,
                              db=Depends(connect_db),
                              token=Depends(get_tokens)):

    result = validate_token(db, token)

    if result["user_type"] != "warehouse-manager" and result["user_type"] != "Administrator":
        raise HTTPException(status_code=403, detail="Unauthorized")

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT total_quantity, order_status
        FROM orders
        WHERE order_id = %s
    """, (data.order_id,))

    order = cursor.fetchone()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["order_status"] not in ["Accepted", "Partial"]:
        raise HTTPException(status_code=400,
                            detail="Order not in valid state")

    cursor.execute("""
        INSERT INTO order_fulfillments 
        (order_id, note, action_by_mobile, action_by_name)
        VALUES (%s, %s, %s, %s)
    """, (
        data.order_id,
        data.notes,
        result["mobile_number"],
        result["user_name"]
    ))

    fulfillment_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO order_timeline 
        (order_id, action_type, message, note, action_by_mobile, action_by_name)
        VALUES (%s, 'Partial', 'Partial fulfillment done', %s, %s, %s)
    """, (
        data.order_id,
        data.notes,
        result["mobile_number"],
        result["user_name"]
    ))

    # Update items
    for item in data.items:
        cursor.execute("""
            SELECT quantity, fulfilled
            FROM order_items
            WHERE order_id = %s AND product_code = %s
        """, (data.order_id, item.product_code))

        db_item = cursor.fetchone()

        if not db_item:
            raise HTTPException(status_code=404,
                                detail=f"{item.product_code} not found")

        # if item.fulfilled > db_item["quantity"]:
        #     raise HTTPException(status_code=400,
        #                         detail="Fulfilled exceeds quantity")

        fulfilled = db_item["fulfilled"] + item.fulfilled

        cursor.execute("""
            UPDATE order_items
            SET fulfilled = %s
            WHERE order_id = %s AND product_code = %s
        """, (fulfilled, data.order_id, item.product_code))

        cursor.execute("""
            SELECT product_name
            FROM products
            WHERE product_code = %s
        """, (item.product_code,))

        product_name = cursor.fetchone()["product_name"]

        cursor.execute("""
            INSERT INTO order_fulfillment_items
            (fulfillment_id, product_code, product_name, fulfilled_quantity)
            VALUES (%s, %s, %s, %s)
        """, (
            fulfillment_id,
            item.product_code,
            product_name,
            item.fulfilled
        ))

    # Recalculate total
    cursor.execute("""
        SELECT SUM(fulfilled) as total
        FROM order_items
        WHERE order_id = %s
    """, (data.order_id,))

    total_fulfilled = cursor.fetchone()["total"] or 0

    # Decide status
    if total_fulfilled >= order["total_quantity"]:
        fulfillment_type = "Final Completion"
        status_color = "#2c7d3a"
        status_val = "Completed"
    else:
        fulfillment_type = "Partial Fulfillment"
        status_color = "#b72b30"
        status_val = "Partial"
        
    cursor.execute("""
        UPDATE order_fulfillments
        SET fulfillment_type = %s, status_color = %s
        WHERE fulfillment_id = %s
    """, (fulfillment_type, status_color, fulfillment_id))

    cursor.execute("""
        UPDATE orders
        SET total_fulfilled = %s,
            order_status = %s,
            notes = %s,
            processed_by = %s
        WHERE order_id = %s
    """, (total_fulfilled, status_val, data.notes, result["mobile_number"], data.order_id))

    db.commit()
    cursor.close()

    return {
        "message": {
            "msg": "Partial update successful",
            "status": "Success"
        }
    }


@app.post("/complete-order")
async def complete_order(data: EachOrderRequest,
                         db=Depends(connect_db),
                         token=Depends(get_tokens)):

    result = validate_token(db, token)

    if result["user_type"] != "warehouse-manager" and result["user_type"] != "Administrator":
        raise HTTPException(status_code=403, detail="Unauthorized")

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT order_status
        FROM orders
        WHERE order_id = %s
    """, (data.order_id,))

    order = cursor.fetchone()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["order_status"] not in ["Accepted", "Partial"]:
        raise HTTPException(status_code=400,
                            detail="Cannot complete this order")
        
    cursor.execute("""
        UPDATE order_items
        SET fulfilled = quantity
        WHERE order_id = %s
    """, (data.order_id,))
    
        
    cursor.execute("""
        UPDATE orders
        SET order_status = 'Completed',
            processed_by = %s,
            total_fulfilled = total_quantity
        WHERE order_id = %s
    """, (result["mobile_number"], data.order_id))
    
    cursor.execute("""
        INSERT INTO order_timeline 
        (order_id, action_type, message, action_by_mobile, action_by_name)
        VALUES (%s, 'Completed', 'Order Completed', %s, %s)
    """, (
        data.order_id,
        result["mobile_number"],
        result["user_name"]
    ))

    db.commit()
    cursor.close()

    return {
        "message": {
            "msg": "Order completed",
            "status": "Success"
        }
    }
    
    
@app.post("/update-invoice-status")
async def update_invoice_status(data: UpdateInvoiceStatusRequest,
                        db=Depends(connect_db),
                        token=Depends(get_tokens)):

    result = validate_token(db, token)

    if result["user_type"] != "contributor":
        raise HTTPException(status_code=403, detail="Unauthorized")


    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT invoice_status
        FROM orders
        WHERE order_id = %s
    """, (data.order_id,))

    order = cursor.fetchone()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    updated_status = None

    if order["invoice_status"] == "Not Flagged":
        updated_status = "Invoiced"
    elif order["invoice_status"] == "Invoiced":
        updated_status = "Not Invoiced"
    elif order["invoice_status"] == "Not Invoiced":
        updated_status = "Invoiced"
    else:
        raise HTTPException(status_code=400, detail="Invalid current invoice status")
        
        
    

    cursor.execute("""
        UPDATE orders
        SET invoice_status = %s
        WHERE order_id = %s
    """, (updated_status, data.order_id))

    cursor.execute("""
        INSERT INTO order_timeline 
        (order_id, action_type, message, action_by_mobile, action_by_name)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        data.order_id,
        "Invoice Updated",
        f"Order marked as {updated_status}",
        result["mobile_number"],
        result["user_name"]
    ))

    db.commit()
    cursor.close()

    return {
        "message": {
            "msg": f"Order marked as {updated_status}",
            "status": "Success"
        }
    }


@app.post("/export-order-pdf")
async def export_order_pdf(
    data: OrderPDFRequest,
    db=Depends(connect_db),
    token=Depends(get_tokens)
):
    
    validate_token(db, token)
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
           SELECT 
                o.order_id, o.order_number,
                o.total_items, o.total_quantity,o.total_fulfilled,
                o.order_status, o.invoice_status,
                o.total_amount, o.created_at,
                c.customer_id, c.business_name,c.godown_id,g.godown_name,
                r.region_name,
                u.user_name AS sales_agent_name,
                o.sales_agent_mobile,
                u1.user_name AS processed_by_name,
                u1.mobile_number AS processed_by_mobile
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN regions r ON c.region_id = r.region_id
            LEFT JOIN godowns g ON c.godown_id = g.godown_id
            JOIN customer_sales_agents csa 
                ON c.customer_id = csa.customer_id
            LEFT JOIN users u ON csa.sales_agent_mobile = u.mobile_number
            LEFT JOIN users u1 ON o.processed_by = u1.mobile_number
            WHERE o.order_id = %s
        """, (data.order_id,))
    order = cursor.fetchone()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    cursor.execute("""
        SELECT 
            oi.product_code,
            p.product_name,
            c.category_name,
            oi.quantity,
            oi.price_per_unit,oi.fulfilled,
            oi.total_price
        FROM order_items oi
        JOIN products p ON oi.product_code = p.product_code
        LEFT JOIN category c ON p.product_category = c.category_id
        WHERE oi.order_id = %s
    """, (data.order_id,))
    
    items = cursor.fetchall()
    
    cursor.close()
    
    os.makedirs("uploads/PDFs", exist_ok=True)
    file_name = f"order_{data.order_id}.pdf"
    file_path = f"uploads/PDFs/{file_name}"
    doc = SimpleDocTemplate(
        file_path,
        pagesize=A6,
        leftMargin=8*mm,
        rightMargin=8*mm,
        topMargin=8*mm,
        bottomMargin=8*mm
    )
    
    styles = getSampleStyleSheet()
    elements = []
    
    build_order_section(order, items, elements, styles)
    doc.build(elements)
    
    pdf_url = f"https://orders.soni.in/orders/download/pdf/{file_name}"

    return {
        "message": {
            "msg": "PDF generated successfully",
            "status": "Success",
            "data": {
                "pdf_url": pdf_url
            }
        }
    }

@app.get("/download/pdf/{file_name}")
async def download_pdf(file_name: str):

    file_path = f"uploads/PDFs/{file_name}"

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type='application/pdf',
        content_disposition_type="attachment"
    )
    
@app.post("/export-multiple-orders-pdf")
async def export_multiple_orders_pdf(
    data: MultipleOrdersPDFRequest,
    db=Depends(connect_db),
    token=Depends(get_tokens)
):

    validate_token(db, token)

    cursor = db.cursor(dictionary=True)

    os.makedirs("uploads/PDFs", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    pdf_file_name = f"orders_{timestamp}.pdf"

    pdf_path = f"uploads/PDFs/{pdf_file_name}"

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A6,
        leftMargin=8*mm,
        rightMargin=8*mm,
        topMargin=8*mm,
        bottomMargin=8*mm
    )

    styles = getSampleStyleSheet()

    elements = []

    total_orders = len(data.order_ids)

    for index, order_id in enumerate(data.order_ids):

        # ======================
        # ORDER
        # ======================

        cursor.execute("""
            SELECT
                o.order_id,
                o.order_number,

                o.total_items,
                o.total_quantity,
                o.total_fulfilled,

                o.order_status,
                o.invoice_status,

                o.total_amount,
                o.created_at,

                c.customer_id,
                c.business_name,
                c.godown_id,
                g.godown_name,

                r.region_name,

                u.user_name AS sales_agent_name,

                o.sales_agent_mobile,

                u1.user_name AS processed_by_name,
                u1.mobile_number AS processed_by_mobile

            FROM orders o

            JOIN customers c
                ON o.customer_id=c.customer_id

            LEFT JOIN regions r
                ON c.region_id=r.region_id
                
            LEFT JOIN godowns g
                ON c.godown_id=g.godown_id

            JOIN customer_sales_agents csa
                ON c.customer_id=csa.customer_id

            LEFT JOIN users u
                ON csa.sales_agent_mobile=u.mobile_number

            LEFT JOIN users u1
                ON o.processed_by=u1.mobile_number

            WHERE o.order_id=%s
        """, (order_id,))

        order = cursor.fetchone()

        if not order:
            continue

        # ======================
        # ITEMS
        # ======================

        cursor.execute("""
            SELECT

                oi.product_code,

                p.product_name,

                c.category_name,

                oi.quantity,

                oi.price_per_unit,

                oi.fulfilled,

                oi.total_price

            FROM order_items oi

            JOIN products p
                ON oi.product_code=p.product_code

            LEFT JOIN category c
                ON p.product_category=c.category_id

            WHERE oi.order_id=%s
        """, (order_id,))

        items = cursor.fetchall()

        # ======================
        # BUILD PAGE
        # ======================

        build_order_section(
            order,
            items,
            elements,
            styles
        )

        # PAGE BREAK

        if index != total_orders - 1:

            elements.append(
                PageBreak()
            )

    cursor.close()

    doc.build(elements)

    pdf_url = (
        f"https://orders.soni.in/"
        f"orders/download/pdf/"
        f"{pdf_file_name}"
    )

    return {
        "message": {
            "msg": "PDF generated successfully",
            "status": "Success",
            "data": {
                "pdf_url": pdf_url
            }
        }
    }  
    
@app.get("/download/zip/{file_name}")
async def download_zip(file_name: str):

    file_path = f"uploads/ZIPs/{file_name}"

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/octet-stream",
        content_disposition_type="attachment"
    )
