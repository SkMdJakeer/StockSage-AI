import pandas as pd


def dashboard_metrics(data):
    products = data["products"]
    inventory = data["inventory"]
    sales = data["sales"]

    total_sales = float(sales["revenue"].sum())
    total_units = int(inventory["quantity"].sum())

    risk = get_stock_risk(data)
    overstock = get_overstock(data)

    return {
        "total_sales": round(total_sales, 2),
        "inventory_units": total_units,
        "products_at_risk": len(risk),
        "overstocked_products": len(overstock),
        "product_count": len(products),
        "store_count": len(data["stores"]),
    }


def get_stock_risk(data):
    products = data["products"]
    inventory = data["inventory"]
    sales = data["sales"]

    recent_date = sales["sale_date"].max()
    start_date = recent_date - pd.Timedelta(days=14)

    recent_sales = (
        sales[sales["sale_date"] >= start_date]
        .groupby("product_id")["quantity"]
        .sum()
        .reset_index()
    )

    recent_sales["avg_daily_sales"] = recent_sales["quantity"] / 14

    result = inventory.merge(
        products[["product_id", "product_name", "reorder_level"]],
        on="product_id",
        how="left",
    )

    result = result.merge(
        recent_sales[["product_id", "avg_daily_sales"]],
        on="product_id",
        how="left",
    )

    result["avg_daily_sales"] = result["avg_daily_sales"].fillna(0)

    result["days_remaining"] = result.apply(
        lambda row:
        row["quantity"] / row["avg_daily_sales"]
        if row["avg_daily_sales"] > 0
        else 999,
        axis=1,
    )

    risk = result[result["days_remaining"] <= 10].copy()

    risk["risk"] = risk["days_remaining"].apply(
        lambda x: "HIGH" if x <= 5 else "MEDIUM"
    )

    risk["days_remaining"] = risk["days_remaining"].round(1)

    return risk.sort_values("days_remaining")


def get_overstock(data):
    products = data["products"]
    inventory = data["inventory"]
    sales = data["sales"]

    recent_date = sales["sale_date"].max()
    start_date = recent_date - pd.Timedelta(days=30)

    recent_sales = (
        sales[sales["sale_date"] >= start_date]
        .groupby("product_id")["quantity"]
        .sum()
        .reset_index()
    )

    recent_sales["avg_daily_sales"] = recent_sales["quantity"] / 30

    result = inventory.groupby("product_id", as_index=False)["quantity"].sum()

    result = result.merge(
        products[["product_id", "product_name"]],
        on="product_id",
        how="left",
    )

    result = result.merge(
        recent_sales[["product_id", "avg_daily_sales"]],
        on="product_id",
        how="left",
    )

    result["avg_daily_sales"] = result["avg_daily_sales"].fillna(0)

    result["days_of_stock"] = result.apply(
        lambda row:
        row["quantity"] / row["avg_daily_sales"]
        if row["avg_daily_sales"] > 0
        else 999,
        axis=1,
    )

    overstock = result[result["days_of_stock"] >= 60].copy()

    overstock["days_of_stock"] = overstock["days_of_stock"].round(1)

    return overstock.sort_values(
        "days_of_stock",
        ascending=False
    )


def sales_change(data, product_name=None):
    products = data["products"]
    sales = data["sales"]

    latest = sales["sale_date"].max()

    current_start = latest - pd.Timedelta(days=14)
    previous_start = latest - pd.Timedelta(days=28)

    current = sales[sales["sale_date"] >= current_start]
    previous = sales[
        (sales["sale_date"] >= previous_start)
        & (sales["sale_date"] < current_start)
    ]

    current_group = (
        current.groupby("product_id")["quantity"]
        .sum()
        .reset_index(name="current_units")
    )

    previous_group = (
        previous.groupby("product_id")["quantity"]
        .sum()
        .reset_index(name="previous_units")
    )

    result = products[["product_id", "product_name"]].merge(
        current_group,
        on="product_id",
        how="left",
    )

    result = result.merge(
        previous_group,
        on="product_id",
        how="left",
    )

    result[["current_units", "previous_units"]] = result[
        ["current_units", "previous_units"]
    ].fillna(0)

    result["change_percent"] = result.apply(
        lambda row:
        ((row["current_units"] - row["previous_units"])
         / row["previous_units"] * 100)
        if row["previous_units"] > 0
        else 0,
        axis=1,
    )

    if product_name:
        result = result[
            result["product_name"].str.contains(
                product_name,
                case=False,
                na=False,
            )
        ]

    result["change_percent"] = result["change_percent"].round(1)

    return result.sort_values(
        "change_percent"
    )


def attention_summary(data):
    risk = get_stock_risk(data)
    overstock = get_overstock(data)
    changes = sales_change(data)

    declines = changes[
        changes["change_percent"] <= -20
    ].head(5)

    return {
        "stock_risk": risk[
            [
                "product_id",
                "product_name",
                "quantity",
                "avg_daily_sales",
                "days_remaining",
                "risk",
            ]
        ].to_dict(orient="records"),

        "overstock": overstock[
            [
                "product_id",
                "product_name",
                "quantity",
                "days_of_stock",
            ]
        ].to_dict(orient="records"),

        "sales_declines": declines[
            [
                "product_id",
                "product_name",
                "current_units",
                "previous_units",
                "change_percent",
            ]
        ].to_dict(orient="records"),
    }