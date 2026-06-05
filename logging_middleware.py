from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import json
import asyncio
from utils.logger import save_log
from validate_token import validate_token,get_tokens
from db_config import connect_db

class LoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        try:
            

            # ✅ Extract request body
            content_type = request.headers.get("content-type", "")
            raw_body = await request.body()

            SKIP_LOG_ENDPOINTS = [
                "/uploads/products/",
            ]

            # if "application/json" in content_type:
            #     try:
            #         request_body = json.loads(raw_body)
            #     except:
            #         request_body = raw_body.decode("utf-8")

            # elif "multipart/form-data" in content_type:
            #     request_body = "FILE UPLOAD"

            # else:
            #     request_body = raw_body.decode("utf-8")
            
            parsed_request_body = None

            if "application/json" in content_type:
                try:
                    parsed_request_body = json.loads(raw_body)
                except:
                    parsed_request_body = raw_body.decode("utf-8")

            elif "multipart/form-data" in content_type:
                parsed_request_body = "FILE UPLOAD"

            else:
                parsed_request_body = raw_body.decode("utf-8")

            # Use parsed_request_body for logic
            request_body = parsed_request_body

            # Save-safe version
            try:
                request_body_str = json.dumps(parsed_request_body, default=str)
            except:
                request_body_str = str(parsed_request_body)
                
            # print(f"Logging Middleware - Request Body: {request_body_str}")
                

            # ✅ Extract user (non-blocking safe)
            user_mobile = None
            user_name = None
            user_type = None
            status_message = None
            latitude = None
            longitude = None

            try:
                # ✅ Case 1: GET → from query params
                if request.method == "GET":
                    latitude = request.query_params.get("latitude")
                    longitude = request.query_params.get("longitude")

                # ✅ Case 2: JSON body
                elif isinstance(request_body, dict):
                    latitude = request_body.get("latitude")
                    longitude = request_body.get("longitude")

                # ✅ Case 3: form-data (fallback, since you set FILE UPLOAD)
                elif "multipart/form-data" in content_type:
                    form = await request.form()
                    latitude = form.get("latitude")
                    longitude = form.get("longitude")

            except:
                pass
            
            try:
                db_gen = connect_db()
                db = next(db_gen)

                token = get_tokens(request.headers.get("Authorization"))
                if token:
                    # token = token.replace("Bearer ", "")
                    result = validate_token(db, token)
                    user_mobile = result.get("mobile_number")
                    user_name = result.get("user_name")
                    user_type = result.get("user_type")

            except:
                pass

            # ✅ Process request FIRST (important)
            # response = await call_next(request)
            
            response = await call_next(request)
            # Skip logging for configured endpoints and favicon
            if any(request.url.path.startswith(ep) for ep in SKIP_LOG_ENDPOINTS) or request.url.path == "/favicon.ico":
                return response
            response_body = b""

            async for chunk in response.body_iterator:
                response_body += chunk
            
            # response.body_iterator = iter([response_body])

            try:
                body_json = json.loads(response_body)
                if "message" in body_json and isinstance(body_json["message"], dict):
                    status_message = body_json["message"].get("msg")
                elif "detail" in body_json:
                    status_message = body_json["detail"]
                else:
                    status_message = str(body_json)[:1000]  
            except:
                status_message = "Unable to parse response body"

            async def new_body_iterator():
                yield response_body 
            
            response.body_iterator = new_body_iterator()

            # ✅ Prepare log data
            log_data = {
                "user_mobile": user_mobile,
                "user_name": user_name,
                "user_type": user_type,
                "endpoint": request.url.path,
                "method": request.method,
                "request_body": request_body_str,
                "status": response.status_code,
                "status_message": status_message,
                "ip": request.client.host,
                "latitude": latitude,
                "longitude": longitude
            }

            # ✅ Run logging in background (NON-BLOCKING)
            asyncio.create_task(asyncio.to_thread(save_log, log_data))

            return response
        except Exception as e:
            print("Logging Middleware Error:", str(e))
            return await call_next(request)  # Proceed without logging on error