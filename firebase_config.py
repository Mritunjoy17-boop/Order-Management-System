import firebase_admin
from firebase_admin import credentials

def initialize_firebase():
    if not firebase_admin._apps:

        cred = credentials.Certificate(
            "/var/www/orders.soni.in/inventory_api/firebase_key.json"
        )
        firebase_admin.initialize_app(cred)
