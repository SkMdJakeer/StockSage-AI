from pathlib import Path
import sys

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import uvicorn


BASE_DIR = Path(__file__).resolve().parent

sys.path.insert(
    0,
    str(BASE_DIR)
)

from src.database import load_data
from src.analytics import (
    dashboard_metrics,
    get_stock_risk,
    get_overstock,
    sales_change,
)
from src.copilot import answer_question


load_dotenv()

app = FastAPI(
    title="StockSage AI",
    description="Retail Sales and Inventory Copilot",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/frontend",
    StaticFiles(directory=BASE_DIR / "frontend"),
    name="frontend",
)


DATA = load_data()


@app.get("/")
def home():
    return FileResponse(
        BASE_DIR / "frontend" / "index.html"
    )


@app.get("/api/metrics")
def metrics():
    return dashboard_metrics(DATA)


@app.get("/api/stock-risk")
def stock_risk():
    return {
        "items": get_stock_risk(DATA)
        .head(10)
        .to_dict(orient="records")
    }


@app.get("/api/overstock")
def overstock():
    return {
        "items": get_overstock(DATA)
        .head(10)
        .to_dict(orient="records")
    }


@app.get("/api/sales-change")
def sales_change_api():
    return {
        "items": sales_change(DATA)
        .head(10)
        .to_dict(orient="records")
    }


@app.post("/api/copilot")
def copilot(payload: dict):
    question = payload.get(
        "question",
        ""
    ).strip()

    if not question:
        return {
            "answer": "Please enter a question.",
            "facts": {},
        }

    return answer_question(
        question,
        DATA,
    )


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )