from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import json
from db_config import connect_db


class LoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        db_gen = connect_db()
        db = next(db_gen)
        cursor = db.cursor()

        try:

            user_mobile = None
            user_name = None
            user_type = None

            # Try extracting token
            try:
                token = request.headers.get("Authorization")
                if token:
                    token = token.replace("Bearer ", "")
                    result = validate_token(db, token)
                    user_mobile = result.get("mobile_number")
                    user_name = result.get("user_name")
                    user_type = result.get("user_type")
            except:
                pass

            # Read request body
            try:
                content_type = request.headers.get("Content-Type", "")
                raw_body = await request.body()
                if "application/json" in content_type:
                    try:
                        request_body = json.loads(raw_body.decode())
                    except:
                        request_body = raw_body.decode("utf-8")  # Store raw body if JSON parsing fails
                elif "multipart/form-data" in content_type:
                    request_body = "File Upload"
                else:
                    request_body = raw_body.decode("utf-8")  # Store raw body for other content types
            except Exception as e:
                request_body = f"Error reading body: {str(e)}" 

            # Process request
            response = await call_next(request)

            # Insert log
            cursor.execute("""
                INSERT INTO api_logs
                (user_mobile, user_name, user_type,
                endpoint, method, request_body,
                response_status, ip_address)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                user_mobile,
                user_name,
                user_type,
                request.url.path,
                request.method,
                request_body,
                response.status_code,
                request.client.host
            ))

            db.commit()
        finally:
            cursor.close()
            try:
                next(db_gen)  # Close the DB connection
            except:
                pass

        return response