"""
inventory_optimizer.py
----------------------
Core analytics: EOQ, Reorder Point, Safety Stock, KPIs.
Works with the merged Kaggle DataFrame from data_loader.py.
"""

import pandas as pd
import numpy as np


def aggregate_product_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Roll weekly rows up to one summary row per (Store, Dept)."""
    agg = (
        df.groupby(["Store", "Dept"])
        .agg(
            Store_Type       =("Type",             "first"),
            Store_Size       =("Size",             "first"),
            Annual_Units     =("Weekly_Units",     lambda x: x.mean() * 52),
            Avg_Weekly_Units =("Weekly_Units",     "mean"),
            Std_Weekly_Units =("Weekly_Units",     "std"),
            Avg_Weekly_Sales =("Weekly_Sales",     "mean"),
            Total_Revenue    =("Weekly_Sales",     "sum"),
            Unit_Price       =("Unit_Price",       "mean"),
            Holding_Cost_Rate=("Holding_Cost_Rate","mean"),
            Order_Cost       =("Order_Cost",       "mean"),
            Stockout_Events  =("Stockout_Flag",    "sum"),
            Weeks_Observed   =("Date",             "count"),
            IsHoliday_Weeks  =("IsHoliday",        "sum"),
            Avg_Markdown     =("Total_MarkDown",   "mean"),
        )
        .reset_index()
    )
    agg["Holding_Cost_Per_Unit"] = agg["Unit_Price"] * agg["Holding_Cost_Rate"]
    return agg


def calculate_eoq(annual_demand, order_cost, holding_cost):
    if holding_cost <= 0 or annual_demand <= 0:
        return 0.0
    return round(np.sqrt((2 * annual_demand * order_cost) / holding_cost), 1)


def calculate_safety_stock(std_weekly_demand, lead_time_weeks, service_level=0.95):
    z_scores = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
    z = z_scores.get(round(service_level, 2), 1.645)
    return round(z * std_weekly_demand * np.sqrt(lead_time_weeks), 1)


def calculate_reorder_point(avg_weekly_demand, lead_time_weeks, safety_stock):
    return round((avg_weekly_demand * lead_time_weeks) + safety_stock, 1)


def calculate_inventory_metrics(df_agg, lead_time_weeks=2.0, service_level=0.95):
    rows = []
    for _, row in df_agg.iterrows():
        ss  = calculate_safety_stock(row["Std_Weekly_Units"], lead_time_weeks, service_level)
        eoq = calculate_eoq(row["Annual_Units"], row["Order_Cost"], row["Holding_Cost_Per_Unit"])
        rop = calculate_reorder_point(row["Avg_Weekly_Units"], lead_time_weeks, ss)

        annual_orders        = round(row["Annual_Units"] / eoq, 1) if eoq > 0 else 0
        annual_ordering_cost = annual_orders * row["Order_Cost"]
        annual_holding_cost  = (eoq / 2) * row["Holding_Cost_Per_Unit"]
        total_inv_cost       = round(annual_ordering_cost + annual_holding_cost, 2)
        stockout_rate        = round(row["Stockout_Events"] / max(row["Weeks_Observed"], 1) * 100, 1)

        rows.append({
            **row.to_dict(),
            "Safety_Stock":         ss,
            "EOQ":                  eoq,
            "Reorder_Point":        rop,
            "Annual_Orders":        annual_orders,
            "Annual_Ordering_Cost": round(annual_ordering_cost, 2),
            "Annual_Holding_Cost":  round(annual_holding_cost, 2),
            "Total_Inventory_Cost": total_inv_cost,
            "Stockout_Rate_Pct":    stockout_rate,
            "Lead_Time_Weeks":      lead_time_weeks,
            "Service_Level":        service_level,
        })
    return pd.DataFrame(rows)


def compute_kpis(df_metrics):
    return {
        "total_skus":           len(df_metrics),
        "avg_eoq":              round(df_metrics["EOQ"].mean(), 0),
        "avg_rop":              round(df_metrics["Reorder_Point"].mean(), 0),
        "avg_safety_stock":     round(df_metrics["Safety_Stock"].mean(), 0),
        "total_inventory_cost": round(df_metrics["Total_Inventory_Cost"].sum(), 2),
        "avg_stockout_rate":    round(df_metrics["Stockout_Rate_Pct"].mean(), 1),
        "high_risk_skus":       int((df_metrics["Stockout_Rate_Pct"] > 30).sum()),
        "total_revenue":        round(df_metrics["Total_Revenue"].sum(), 2),
    }


def weekly_demand_trend(df, store, dept):
    mask  = (df["Store"] == store) & (df["Dept"] == dept)
    trend = df[mask][["Date","Weekly_Units","Weekly_Sales","IsHoliday","Total_MarkDown"]].copy()
    trend["Rolling_Avg"] = trend["Weekly_Units"].rolling(4, min_periods=1).mean()
    return trend


def eoq_sensitivity(base_demand, base_order_cost, base_holding_cost, n=25):
    order_costs = np.linspace(base_order_cost * 0.5, base_order_cost * 1.5, n)
    eoqs        = [calculate_eoq(base_demand, oc, base_holding_cost) for oc in order_costs]
    return pd.DataFrame({"Order_Cost": order_costs, "EOQ": eoqs})
