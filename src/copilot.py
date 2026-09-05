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


MODEL_NAME = "gemini-3.7-flash"


# ============================================================
# GEMINI CLIENT
# ============================================================

def create_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    return genai.Client(api_key=api_key)


# ============================================================
# PRODUCT DETECTION
# ============================================================

def find_product(question, data):
    question_lower = question.lower()

    for _, row in data["products"].iterrows():
        product_name = str(row["product_name"])

        if product_name.lower() in question_lower:
            return product_name

        words = product_name.lower().split()

        if len(words) >= 2:
            if all(word in question_lower for word in words):
                return product_name

    return None


# ============================================================
# FACT EXTRACTION
# ============================================================

def get_facts(question, data):
    q = question.lower()

    facts = {
        "dashboard": dashboard_metrics(data)
    }

    product_name = find_product(question, data)

    # --------------------------------------------------------
    # Unsupported external-data questions
    # --------------------------------------------------------

    unsupported_topics = [
        "advertising",
        "advertisement",
        "marketing",
        "campaign",
        "competitor",
        "competition",
        "weather",
        "social media",
    ]

    unsupported = [
        topic for topic in unsupported_topics
        if topic in q
    ]

    if unsupported:
        facts["limitation"] = (
            "The available dataset contains product, store, "
            "inventory and sales data only. It does not contain "
            "advertising, marketing, competitor, weather or "
            "social-media data."
        )

    # --------------------------------------------------------
    # ATTENTION
    # --------------------------------------------------------

    if any(word in q for word in [
        "attention",
        "today",
        "urgent",
        "priority",
        "critical",
    ]):
        facts["attention"] = attention_summary(data)

    # --------------------------------------------------------
    # STOCK RISK / REORDER
    # --------------------------------------------------------

    if any(word in q for word in [
        "reorder",
        "stockout",
        "stock-out",
        "inventory",
        "stock",
        "replenish",
    ]):
        risk = get_stock_risk(data)

        if product_name:
            risk = risk[
                risk["product_name"].str.contains(
                    product_name,
                    case=False,
                    na=False,
                )
            ]

        facts["stock_risk"] = (
            risk.head(10)
            .to_dict(orient="records")
        )

    # --------------------------------------------------------
    # OVERSTOCK
    # --------------------------------------------------------

    if any(word in q for word in [
        "overstock",
        "overstocked",
        "slow moving",
        "slow-moving",
        "non-moving",
        "excess stock",
    ]):
        overstock = get_overstock(data)

        if product_name:
            overstock = overstock[
                overstock["product_name"].str.contains(
                    product_name,
                    case=False,
                    na=False,
                )
            ]

        facts["overstock"] = (
            overstock.head(10)
            .to_dict(orient="records")
        )

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    if any(word in q for word in [
        "sales",
        "sale",
        "decline",
        "drop",
        "fell",
        "fall",
        "increase",
        "increased",
        "spike",
        "trend",
        "performance",
    ]):
        changes = sales_change(
            data,
            product_name=product_name,
        )

        facts["sales_change"] = (
            changes.head(10)
            .to_dict(orient="records")
        )

    return facts


# ============================================================
# DETERMINISTIC ANSWERS
# ============================================================

def deterministic_answer(question, facts):

    q = question.lower()

    # --------------------------------------------------------
    # LIMITATION / REFUSAL
    # --------------------------------------------------------

    if "limitation" in facts:
        return (
            "The available data is insufficient to answer that.\n\n"

            "Finding\n"
            "The dataset does not contain the external factor "
            "needed to answer this question.\n\n"

            "Evidence\n"
            "StockSage has product, store, inventory and sales "
            "data, but no advertising, marketing, competitor, "
            "weather or campaign data.\n\n"

            "Recommended Action\n"
            "Add the relevant external data and compare it with "
            "sales performance before making a causal conclusion.\n\n"

            "Limitation\n"
            "Sales changes can be observed, but their external "
            "cause cannot be established from the available data."
        )

    # --------------------------------------------------------
    # ATTENTION
    # --------------------------------------------------------

    if "attention" in facts:

        attention = facts["attention"]

        risk_items = attention.get(
            "stock_risk",
            []
        )

        overstock_items = attention.get(
            "overstock",
            []
        )

        decline_items = attention.get(
            "sales_declines",
            []
        )

        lines = [
            "Finding",
            "StockSage identified the following priorities "
            "from current sales and inventory data:",
            ""
        ]

        # Stock risk
        if risk_items:
            lines.append("Highest Stock Risks")

            for item in risk_items[:5]:
                lines.append(
                    f"• {item['product_name']} at "
                    f"{item['store_id']}: "
                    f"{int(item['quantity'])} units in stock, "
                    f"{float(item['avg_daily_sales']):.1f} units/day, "
                    f"{float(item['days_remaining']):.1f} days remaining "
                    f"({item['risk']} risk)."
                )

            lines.append("")

        # Overstock
        if overstock_items:
            lines.append("Overstock")

            for item in overstock_items[:3]:
                lines.append(
                    f"• {item['product_name']}: "
                    f"{int(item['quantity'])} units in stock, "
                    f"{float(item['days_of_stock']):.1f} days of stock."
                )

            lines.append("")

        # Sales declines
        if decline_items:
            lines.append("Sales Changes")

            for item in decline_items[:3]:
                lines.append(
                    f"• {item['product_name']}: "
                    f"{float(item['change_percent']):.1f}% decline "
                    f"({int(item['previous_units'])} → "
                    f"{int(item['current_units'])} units)."
                )

            lines.append("")

        lines.extend([
            "Recommended Action",
            "Prioritize products with the fewest days of stock "
            "remaining, then review significant sales declines "
            "and overstock before changing replenishment plans.",
            "",
            "Assumption",
            "Stock coverage is estimated from recent sales demand. "
            "The analysis does not establish external causes for "
            "sales changes."
        ])

        return "\n".join(lines)

    # --------------------------------------------------------
    # REORDER
    # --------------------------------------------------------

    if "stock_risk" in facts and any(
        word in q
        for word in [
            "reorder",
            "replenish",
            "stockout",
            "stock-out",
        ]
    ):

        items = facts["stock_risk"]

        if not items:
            return (
                "No matching stock-risk items were found "
                "in the available data."
            )

        lines = [
            "Finding",
            "The following items have the highest "
            "replenishment priority:",
            ""
        ]

        for item in items[:5]:

            daily_sales = float(
                item["avg_daily_sales"]
            )

            days_remaining = float(
                item["days_remaining"]
            )

            current_stock = int(
                item["quantity"]
            )

            # 14 days demand + 20% safety buffer
            reorder_quantity = max(
                0,
                round(
                    daily_sales * 14 * 1.2
                    - current_stock
                )
            )

            lines.append(
                f"• {item['product_name']} at "
                f"{item['store_id']}: "
                f"{current_stock} units in stock, "
                f"{daily_sales:.1f} units/day, "
                f"{days_remaining:.1f} days remaining, "
                f"reorder {reorder_quantity} units."
            )

        lines.extend([
            "",
            "Recommended Action",
            "Prioritize the items with the fewest days "
            "of stock remaining.",
            "",
            "Assumption",
            "Reorder quantity targets 14 days of demand "
            "plus a 20% safety buffer."
        ])

        return "\n".join(lines)

    # --------------------------------------------------------
    # OVERSTOCK
    # --------------------------------------------------------

    if "overstock" in facts:

        items = facts["overstock"]

        if not items:
            return "No overstocked products were identified."

        lines = [
            "Finding",
            "The following products have unusually "
            "high stock coverage:",
            ""
        ]

        for item in items[:5]:
            lines.append(
                f"• {item['product_name']}: "
                f"{int(item['quantity'])} units in stock, "
                f"{float(item['days_of_stock']):.1f} days of stock."
            )

        lines.extend([
            "",
            "Recommended Action",
            "Pause or reduce replenishment for heavily "
            "overstocked items and consider promotion "
            "or inventory rebalancing.",
        ])

        return "\n".join(lines)

    # --------------------------------------------------------
    # SALES CHANGE
    # --------------------------------------------------------

    if "sales_change" in facts:

        items = facts["sales_change"]

        if not items:
            return (
                "No matching sales information "
                "was found."
            )

        lines = [
            "Finding",
            "Recent sales performance compared "
            "with the previous period:",
            ""
        ]

        for item in items[:5]:

            change = float(
                item["change_percent"]
            )

            direction = (
                "increase"
                if change >= 0
                else "decline"
            )

            lines.append(
                f"• {item['product_name']}: "
                f"{abs(change):.1f}% {direction} "
                f"({int(item['previous_units'])} → "
                f"{int(item['current_units'])} units)."
            )

        lines.extend([
            "",
            "Recommendation",
            "Investigate significant changes using "
            "available sales and inventory evidence "
            "before taking action."
        ])

        return "\n".join(lines)

    # --------------------------------------------------------
    # GENERAL DASHBOARD
    # --------------------------------------------------------

    dashboard = facts["dashboard"]

    return (
        "Finding\n"
        f"Total sales are ₹"
        f"{float(dashboard['total_sales']):,.1f} "
        f"across {dashboard['store_count']} stores "
        f"and {dashboard['product_count']} products.\n\n"

        "Evidence\n"
        f"Inventory contains "
        f"{int(dashboard['inventory_units']):,} units. "
        f"{dashboard['products_at_risk']} store-product "
        f"combinations are currently at risk and "
        f"{dashboard['overstocked_products']} are overstocked.\n\n"

        "Recommendation\n"
        "Use the Stock Risk, Sales Changes and Overstock "
        "panels to identify the highest-priority actions."
    )


# ============================================================
# MAIN COPILOT
# ============================================================

def answer_question(question, data):

    facts = get_facts(
        question,
        data
    )

    q = question.lower()

    # --------------------------------------------------------
    # ALWAYS ANSWER THESE DETERMINISTICALLY
    # --------------------------------------------------------
    #
    # These queries are completely answerable from our
    # structured retail data. No Gemini call is necessary.
    # This also prevents quota exhaustion for common dashboard
    # questions.
    # --------------------------------------------------------

    deterministic_topics = [
        "attention",
        "today",
        "urgent",
        "priority",
        "critical",
        "reorder",
        "replenish",
        "stockout",
        "stock-out",
        "overstock",
        "overstocked",
        "slow moving",
        "slow-moving",
        "non-moving",
    ]

    if any(
        word in q
        for word in deterministic_topics
    ):
        return {
            "answer": deterministic_answer(
                question,
                facts
            ),
            "facts": facts,
            "source": "deterministic",
        }

    # --------------------------------------------------------
    # UNSUPPORTED QUESTIONS
    # --------------------------------------------------------

    if "limitation" in facts:
        return {
            "answer": deterministic_answer(
                question,
                facts
            ),
            "facts": facts,
            "source": "deterministic",
        }

    # --------------------------------------------------------
    # TRY GEMINI FOR INTERPRETIVE QUESTIONS
    # --------------------------------------------------------

    client = create_client()

    if client is None:
        return {
            "answer": deterministic_answer(
                question,
                facts
            ),
            "facts": facts,
            "source": "deterministic",
        }

    prompt = build_prompt(
        question,
        json.dumps(
            facts,
            indent=2,
            default=str
        ),
    )

    try:

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        if response and response.text:

            return {
                "answer": response.text.strip(),
                "facts": facts,
                "source": "gemini",
            }

        return {
            "answer": deterministic_answer(
                question,
                facts
            ),
            "facts": facts,
            "source": "deterministic",
        }

    except Exception as error:

        print(
            "Gemini API error:",
            repr(error)
        )

        # IMPORTANT:
        # Gemini failure must NEVER break the application.
        return {
            "answer": deterministic_answer(
                question,
                facts
            ),
            "facts": facts,
            "source": "deterministic_fallback",
        }