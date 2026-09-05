import os
import json

from google import genai

from .analytics import (
    dashboard_metrics,
    get_stock_risk,
    get_overstock,
    sales_change,
    attention_summary,
)

from .prompts import build_prompt


def create_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    return genai.Client(api_key=api_key)


def get_facts(question, data):
    question_lower = question.lower()

    facts = {
        "dashboard": dashboard_metrics(data),
    }

    if any(
        word in question_lower
        for word in [
            "attention",
            "today",
            "urgent",
            "risk",
        ]
    ):
        facts["attention"] = attention_summary(data)

    if any(
        word in question_lower
        for word in [
            "reorder",
            "stock",
            "stockout",
            "stock-out",
            "inventory",
        ]
    ):
        facts["stock_risk"] = get_stock_risk(
            data
        ).head(10).to_dict(orient="records")

    if any(
        word in question_lower
        for word in [
            "overstock",
            "slow",
            "non-moving",
        ]
    ):
        facts["overstock"] = get_overstock(
            data
        ).head(10).to_dict(orient="records")

    if any(
        word in question_lower
        for word in [
            "sales",
            "decline",
            "drop",
            "increase",
            "spike",
            "trend",
        ]
    ):
        facts["sales_change"] = sales_change(
            data
        ).head(10).to_dict(orient="records")

    # Demonstrate evidence-based refusal
    unsupported_topics = [
        "advertising",
        "marketing",
        "weather",
        "competitor",
        "social media",
        "campaign",
    ]

    if any(
        topic in question_lower
        for topic in unsupported_topics
    ):
        facts["limitation"] = (
            "The available dataset contains product, store, "
            "inventory and sales data. It does not contain "
            "the requested external factor."
        )

    return facts


def answer_question(question, data):
    facts = get_facts(question, data)

    client = create_client()

    if client is None:
        return {
            "answer": (
                "Gemini is not configured yet. "
                "Set GEMINI_API_KEY in the .env file "
                "to enable the AI copilot."
            ),
            "facts": facts,
        }

    prompt = build_prompt(
        question,
        json.dumps(facts, indent=2, default=str),
    )

    try:
        response = client.models.generate_content(
            model="gemini-3.7-flash",
            contents=prompt,
        )

        return {
            "answer": response.text,
            "facts": facts,
        }

    except Exception as error:
        return {
            "answer": (
                "I couldn't contact Gemini right now. "
                "The deterministic retail analysis is still available."
            ),
            "facts": facts,
            "error": str(error),
        }