# master.py
from fastapi import FastAPI, Request
from login_api.login import app as login_app
from categories_api.categories import app as categories_app
from products_api.products import app as products_app
from godown_api.godown import app as godown_app
from moulder_api.moulder import app as moulder_app
from units_api.units import app as units_app
from stocks_api.stocks import app as stocks_app
from stocks_api.submit_inward_outward import app as submit_inward_outward_app
from stocks_api.expected_stocks_recon import app as expected_stocks_recon_app
from stocks_api.variance_stocks_recon import app as variance_stocks_recon_app
from version_api.version_check import app as version_check_app
from logout_api.logout import app as logout_app
from fastapi.staticfiles import StaticFiles

from customers_api.customers import app as customers_app
from orders_api.orders import app as orders_app
from regions_api.regions import app as regions_app
from user_management_api.user_management import app as user_management_app
from timeline_api.timeline import app as timeline_app
from fulfillment_api.fulfillment import app as fulfillment_app
from dashboard_api.dashboard import app as dashboard_app
from master_page_api.master_page import app as master_page_app
from reports_page_api.reports import app as reports_app
from logging_middleware import LoggingMiddleware
from logs.logs import app as logs_app
from firebase_config import initialize_firebase


app = FastAPI()

initialize_firebase()
app.add_middleware(LoggingMiddleware)  # Add logging middleware to the main app

# @app.middleware("http")
# async def print_url(request: Request, call_next):

#     print(request.url)

#     response = await call_next(request)
#     print(response)

#     return response


# Mount each app under its own path
app.mount("/login", login_app)
app.mount("/categories", categories_app)
app.mount("/products", products_app)
app.mount("/godown", godown_app)
app.mount("/moulder", moulder_app)
app.mount("/units", units_app)
app.mount("/stocks", stocks_app)
app.mount("/submit_inward_outward", submit_inward_outward_app)
app.mount("/expected_stocks_recon", expected_stocks_recon_app)
app.mount("/variance_stocks_recon", variance_stocks_recon_app)
app.mount("/version_check", version_check_app)
app.mount("/logout", logout_app)

app.mount("/customers", customers_app)
app.mount("/orders", orders_app)
app.mount("/regions", regions_app)
app.mount("/users", user_management_app)
app.mount("/timeline", timeline_app)
app.mount("/fulfillment", fulfillment_app)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.mount("/dashboard", dashboard_app)
app.mount("/masters", master_page_app)
app.mount("/reports", reports_app)
app.mount("/logs", logs_app)
