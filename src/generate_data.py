import csv
import random
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

products = [
    ("P001", "Wireless Headphones"),
    ("P002", "Bluetooth Speaker"),
    ("P003", "Smart Watch"),
    ("P004", "USB-C Charger"),
    ("P005", "Power Bank"),
    ("P006", "Nike Running Shoes"),
    ("P007", "Adidas Sports Shoes"),
    ("P008", "Blue Denim Jacket"),
    ("P009", "Black Hoodie"),
    ("P010", "White T-Shirt"),
    ("P011", "Backpack"),
    ("P012", "Leather Wallet"),
    ("P013", "Sunglasses"),
    ("P014", "Baseball Cap"),
    ("P015", "Formal Shirt"),
    ("P016", "Casual Jeans"),
    ("P017", "Running Shorts"),
    ("P018", "Sports Bottle"),
    ("P019", "Wireless Mouse"),
    ("P020", "Mechanical Keyboard"),
]

stores = ["S001", "S002", "S003"]

prices = {
    "P001": 59.99,
    "P002": 39.99,
    "P003": 89.99,
    "P004": 19.99,
    "P005": 29.99,
    "P006": 119.99,
    "P007": 99.99,
    "P008": 79.99,
    "P009": 49.99,
    "P010": 24.99,
    "P011": 44.99,
    "P012": 34.99,
    "P013": 29.99,
    "P014": 19.99,
    "P015": 54.99,
    "P016": 69.99,
    "P017": 34.99,
    "P018": 14.99,
    "P019": 27.99,
    "P020": 74.99,
}

random.seed(42)

start = date.today() - timedelta(days=89)

rows = []
sale_id = 1

for day_number in range(90):
    current_date = start + timedelta(days=day_number)

    for store in stores:
        for product_id, _ in products:

            base = random.randint(2, 8)

            # Wireless headphones: strong recent decline
            if product_id == "P001" and day_number >= 60:
                base = max(0, int(base * 0.45))

            # Nike shoes: strong demand
            if product_id == "P006":
                base = random.randint(5, 10)

            # Denim jacket: slow-moving product
            if product_id == "P008":
                base = random.randint(0, 2)

            # Weekend boost
            if current_date.weekday() >= 5:
                base = int(base * 1.25)

            quantity = max(0, base)

            if quantity == 0:
                continue

            revenue = round(quantity * prices[product_id], 2)

            rows.append([
                sale_id,
                store,
                product_id,
                current_date.isoformat(),
                quantity,
                revenue
            ])

            sale_id += 1

output = DATA_DIR / "sales.csv"

with open(output, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "sale_id",
        "store_id",
        "product_id",
        "sale_date",
        "quantity",
        "revenue"
    ])
    writer.writerows(rows)

print(f"Generated {len(rows)} sales records.")
print(f"Saved to: {output}")