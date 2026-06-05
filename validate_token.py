from fastapi import HTTPException,Header,status


def get_tokens(authorization : str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid authorization header format"
        )
    token = authorization.split(" ")[1]
    return token

def validate_token(db, token):
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT j.mobile_number,
               j.jwt_status,
               u.user_name,
               u.user_type
        FROM user_jwt j
        JOIN users u ON j.mobile_number = u.mobile_number
        WHERE j.jwt_token = %s
    """, (token,))

    result = cursor.fetchone()
    cursor.close()

    if not result or result['jwt_status'] != 'valid':
        raise HTTPException(
            status_code=401,
            detail={
                "msg": "Token expired",
                "status": "Failure",
                "data": {}
            }
        )

    return result

