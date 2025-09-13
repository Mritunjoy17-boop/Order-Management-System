# master.py
from fastapi import FastAPI
from login_api.login import app as login_app
from categories_api.categories import app as categories_app
from products_api.products import app as products_app
from godown_api.godown import app as godown_app
from moulder_api.moulder import app as moulder_app
from units_api.units import app as units_app
from stocks_api.stocks import app as stocks_app
from logout_api.logout import app as logout_app

app = FastAPI()

# Mount each app under its own path
app.mount("/login", login_app)
app.mount("/categories", categories_app)
app.mount("/products", products_app)
app.mount("/godown", godown_app)
app.mount("/moulder", moulder_app)
app.mount("/units", units_app)
app.mount("/stocks", units_app)
app.mount("/logout", logout_app)