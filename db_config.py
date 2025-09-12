def connect_db():
    import mysql.connector

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