# utils/logger.py
import json
from db_config import connect_db

def save_log(log_data):
    try:
        db_gen = connect_db()
        db = next(db_gen)
        cursor = db.cursor()
        
        # print(log_data, "Logging Data")

        cursor.execute("""
            INSERT INTO api_logs
            (user_mobile, user_name, user_type,
             endpoint, method, request_body,
             response_status, ip_address,status_message, latitude, longitude)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            log_data["user_mobile"],
            log_data["user_name"],
            log_data["user_type"],
            log_data["endpoint"],
            log_data["method"],
            log_data["request_body"],
            log_data["status"],
            log_data["ip"],
            log_data["status_message"],
            log_data["latitude"],
            log_data["longitude"]

        ))

        db.commit()
        cursor.close()

        try:
            next(db_gen)
        except:
            pass

    except Exception as e:
        print("Logging failed:", str(e))