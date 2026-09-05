from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def load_data():
    products = pd.read_csv(DATA_DIR / "products.csv")
    stores = pd.read_csv(DATA_DIR / "stores.csv")
    inventory = pd.read_csv(DATA_DIR / "inventory.csv")
    sales = pd.read_csv(DATA_DIR / "sales.csv")

    sales["sale_date"] = pd.to_datetime(sales["sale_date"])

    return {
        "products": products,
        "stores": stores,
        "inventory": inventory,
        "sales": sales,
    }


def get_product_name(products, product_id):
    row = products[products["product_id"] == product_id]

    if row.empty:
        return product_id

    return row.iloc[0]["product_name"]


def get_store_name(stores, store_id):
    row = stores[stores["store_id"] == store_id]

    if row.empty:
        return store_id

    return row.iloc[0]["store_name"]