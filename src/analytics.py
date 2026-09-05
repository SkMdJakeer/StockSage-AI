import pandas as pd


# ============================================================
# DASHBOARD METRICS
# ============================================================

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


# ============================================================
# STOCK RISK
# Store-specific demand is used for store-specific inventory.
# ============================================================

def get_stock_risk(data):
    products = data["products"]
    inventory = data["inventory"]
    sales = data["sales"]

    latest_date = sales["sale_date"].max()

    # Exactly the latest 14 calendar days
    start_date = latest_date - pd.Timedelta(days=13)

    recent_sales = sales[
        sales["sale_date"].between(start_date, latest_date)
    ]

    demand = (
        recent_sales
        .groupby(["store_id", "product_id"])["quantity"]
        .sum()
        .reset_index(name="recent_units")
    )

    demand["avg_daily_sales"] = demand["recent_units"] / 14

    result = inventory.merge(
        products[
            [
                "product_id",
                "product_name",
                "reorder_level",
            ]
        ],
        on="product_id",
        how="left",
    )

    result = result.merge(
        demand[
            [
                "store_id",
                "product_id",
                "avg_daily_sales",
            ]
        ],
        on=["store_id", "product_id"],
        how="left",
    )

    result["avg_daily_sales"] = result["avg_daily_sales"].fillna(0)

    # Days of inventory remaining
    result["days_remaining"] = result.apply(
        lambda row:
        row["quantity"] / row["avg_daily_sales"]
        if row["avg_daily_sales"] > 0
        else 999,
        axis=1,
    )

    # Risk classification
    result["risk"] = result["days_remaining"].apply(
        lambda days:
        "HIGH"
        if days <= 5
        else "MEDIUM"
        if days <= 10
        else "LOW"
    )

    # Suggested replenishment:
    # 14 days of demand + 20% safety buffer - current stock
    result["reorder_quantity"] = (
        result["avg_daily_sales"] * 14 * 1.20
        - result["quantity"]
    ).clip(lower=0)

    result["days_remaining"] = result["days_remaining"].round(1)

    result["reorder_quantity"] = (
        result["reorder_quantity"]
        .round()
        .astype(int)
    )

    return (
        result[result["days_remaining"] <= 10]
        .sort_values(
            ["days_remaining", "avg_daily_sales"],
            ascending=[True, False],
        )
        .reset_index(drop=True)
    )


# ============================================================
# OVERSTOCK
# Uses 30-day demand and total inventory.
# ============================================================

def get_overstock(data):
    products = data["products"]
    inventory = data["inventory"]
    sales = data["sales"]

    latest_date = sales["sale_date"].max()
    start_date = latest_date - pd.Timedelta(days=29)

    recent_sales = sales[
        sales["sale_date"].between(start_date, latest_date)
    ]

    demand = (
        recent_sales
        .groupby("product_id")["quantity"]
        .sum()
        .reset_index(name="recent_units")
    )

    demand["avg_daily_sales"] = demand["recent_units"] / 30

    stock = (
        inventory
        .groupby("product_id", as_index=False)["quantity"]
        .sum()
    )

    result = stock.merge(
        products[
            [
                "product_id",
                "product_name",
            ]
        ],
        on="product_id",
        how="left",
    )

    result = result.merge(
        demand[
            [
                "product_id",
                "avg_daily_sales",
            ]
        ],
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

    result["days_of_stock"] = result["days_of_stock"].round(1)

    return (
        result[result["days_of_stock"] >= 60]
        .sort_values(
            "days_of_stock",
            ascending=False,
        )
        .reset_index(drop=True)
    )


# ============================================================
# SLOW / NON-MOVING STOCK
# ============================================================

def get_slow_moving(data):
    products = data["products"]
    inventory = data["inventory"]
    sales = data["sales"]

    latest_date = sales["sale_date"].max()
    start_date = latest_date - pd.Timedelta(days=29)

    recent_sales = sales[
        sales["sale_date"].between(start_date, latest_date)
    ]

    demand = (
        recent_sales
        .groupby("product_id")["quantity"]
        .sum()
        .reset_index(name="units_sold_30d")
    )

    stock = (
        inventory
        .groupby("product_id", as_index=False)["quantity"]
        .sum()
    )

    result = stock.merge(
        products[
            [
                "product_id",
                "product_name",
            ]
        ],
        on="product_id",
        how="left",
    )

    result = result.merge(
        demand,
        on="product_id",
        how="left",
    )

    result["units_sold_30d"] = (
        result["units_sold_30d"]
        .fillna(0)
    )

    result["avg_daily_sales"] = (
        result["units_sold_30d"] / 30
    )

    # Slow-moving:
    # 30-day sales <= 30 units AND inventory exists
    result = result[
        (result["quantity"] > 0)
        & (result["units_sold_30d"] <= 30)
    ].copy()

    result["days_of_stock"] = result.apply(
        lambda row:
        row["quantity"] / row["avg_daily_sales"]
        if row["avg_daily_sales"] > 0
        else 999,
        axis=1,
    )

    result["days_of_stock"] = (
        result["days_of_stock"]
        .round(1)
    )

    return result.sort_values(
        "days_of_stock",
        ascending=False,
    ).reset_index(drop=True)


# ============================================================
# SALES CHANGE
# Supports 14-day or 30-day comparisons.
# ============================================================

def sales_change(
    data,
    product_name=None,
    period_days=14,
):
    products = data["products"]
    sales = data["sales"]

    latest_date = sales["sale_date"].max()

    current_start = (
        latest_date
        - pd.Timedelta(days=period_days - 1)
    )

    previous_start = (
        latest_date
        - pd.Timedelta(days=(period_days * 2) - 1)
    )

    current = sales[
        sales["sale_date"].between(
            current_start,
            latest_date,
        )
    ]

    previous = sales[
        sales["sale_date"].between(
            previous_start,
            current_start - pd.Timedelta(days=1),
        )
    ]

    current_group = (
        current
        .groupby("product_id")["quantity"]
        .sum()
        .reset_index(name="current_units")
    )

    previous_group = (
        previous
        .groupby("product_id")["quantity"]
        .sum()
        .reset_index(name="previous_units")
    )

    result = products[
        [
            "product_id",
            "product_name",
        ]
    ].merge(
        current_group,
        on="product_id",
        how="left",
    )

    result = result.merge(
        previous_group,
        on="product_id",
        how="left",
    )

    result[
        [
            "current_units",
            "previous_units",
        ]
    ] = result[
        [
            "current_units",
            "previous_units",
        ]
    ].fillna(0)

    result["change_percent"] = result.apply(
        lambda row:
        (
            (
                row["current_units"]
                - row["previous_units"]
            )
            / row["previous_units"]
            * 100
        )
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

    result["change_percent"] = (
        result["change_percent"]
        .round(1)
    )

    return result.sort_values(
        "change_percent"
    ).reset_index(drop=True)


# ============================================================
# MONTHLY PRODUCT PERFORMANCE
# ============================================================

def monthly_performance(data, product_name=None):
    products = data["products"]
    sales = data["sales"]

    latest_date = sales["sale_date"].max()

    current_start = (
        latest_date
        - pd.Timedelta(days=29)
    )

    previous_start = (
        latest_date
        - pd.Timedelta(days=59)
    )

    current = sales[
        sales["sale_date"].between(
            current_start,
            latest_date,
        )
    ]

    previous = sales[
        sales["sale_date"].between(
            previous_start,
            current_start - pd.Timedelta(days=1),
        )
    ]

    current_group = (
        current
        .groupby("product_id")
        .agg(
            current_units=("quantity", "sum"),
            current_revenue=("revenue", "sum"),
        )
        .reset_index()
    )

    previous_group = (
        previous
        .groupby("product_id")
        .agg(
            previous_units=("quantity", "sum"),
            previous_revenue=("revenue", "sum"),
        )
        .reset_index()
    )

    result = products[
        [
            "product_id",
            "product_name",
        ]
    ].merge(
        current_group,
        on="product_id",
        how="left",
    )

    result = result.merge(
        previous_group,
        on="product_id",
        how="left",
    )

    numeric_columns = [
        "current_units",
        "current_revenue",
        "previous_units",
        "previous_revenue",
    ]

    result[numeric_columns] = (
        result[numeric_columns]
        .fillna(0)
    )

    result["change_percent"] = result.apply(
        lambda row:
        (
            (
                row["current_units"]
                - row["previous_units"]
            )
            / row["previous_units"]
            * 100
        )
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

    result["current_revenue"] = (
        result["current_revenue"]
        .round(2)
    )

    result["previous_revenue"] = (
        result["previous_revenue"]
        .round(2)
    )

    result["change_percent"] = (
        result["change_percent"]
        .round(1)
    )

    return result.reset_index(drop=True)


# ============================================================
# SALES SPIKES
# ============================================================

def get_sales_spikes(data):
    changes = sales_change(
        data,
        period_days=14,
    )

    return (
        changes[
            changes["change_percent"] >= 20
        ]
        .sort_values(
            "change_percent",
            ascending=False,
        )
        .reset_index(drop=True)
    )


# ============================================================
# SALES DECLINES
# ============================================================

def get_sales_declines(data):
    changes = sales_change(
        data,
        period_days=14,
    )

    return (
        changes[
            changes["change_percent"] <= -20
        ]
        .sort_values(
            "change_percent"
        )
        .reset_index(drop=True)
    )


# ============================================================
# ATTENTION SUMMARY
# ============================================================

def attention_summary(data):
    risk = get_stock_risk(data)
    overstock = get_overstock(data)
    slow = get_slow_moving(data)
    spikes = get_sales_spikes(data)
    declines = get_sales_declines(data)

    return {
        "stock_risk": risk[
            [
                "store_id",
                "product_id",
                "product_name",
                "quantity",
                "avg_daily_sales",
                "days_remaining",
                "risk",
                "reorder_quantity",
            ]
        ].head(10).to_dict(
            orient="records"
        ),

        "overstock": overstock[
            [
                "product_id",
                "product_name",
                "quantity",
                "avg_daily_sales",
                "days_of_stock",
            ]
        ].head(10).to_dict(
            orient="records"
        ),

        "slow_moving": slow[
            [
                "product_id",
                "product_name",
                "quantity",
                "units_sold_30d",
                "days_of_stock",
            ]
        ].head(10).to_dict(
            orient="records"
        ),

        "sales_spikes": spikes[
            [
                "product_id",
                "product_name",
                "current_units",
                "previous_units",
                "change_percent",
            ]
        ].head(10).to_dict(
            orient="records"
        ),

        "sales_declines": declines[
            [
                "product_id",
                "product_name",
                "current_units",
                "previous_units",
                "change_percent",
            ]
        ].head(10).to_dict(
            orient="records"
        ),
    }