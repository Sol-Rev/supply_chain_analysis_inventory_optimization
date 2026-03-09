"""
data_loader.py
--------------
Loads and merges the real Kaggle Walmart dataset (3 files).

File auto-discovery — looks in these locations automatically:
  1. Same folder as app.py      → train.csv / features.csv / stores.csv
  2. data/ subfolder            → data/train.csv  etc.
  3. files/ subfolder           → files/train.csv etc.

Supports both .csv and .xlsx extensions.
"""

import pandas as pd
import numpy as np
import os

# Folder where this script lives
_HERE = os.path.dirname(os.path.abspath(__file__))


def _find_file(name: str) -> str:
    """Search for `name` file across common locations. Returns first match."""
    exts    = [".csv", ".xlsx", ".xls"]
    subdirs = ["", "data", "files"]

    candidates = []
    for sub in subdirs:
        base = os.path.join(_HERE, sub) if sub else _HERE
        for ext in exts:
            candidates.append(os.path.join(base, name + ext))

    for path in candidates:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(
        f"Cannot find '{name}' file. Tried:\n" +
        "\n".join(f"  {c}" for c in candidates) +
        "\n\nPlace train.csv, features.csv, stores.csv in the same folder as app.py."
    )


def _read(path: str) -> pd.DataFrame:
    """Read CSV or Excel transparently."""
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    return pd.read_csv(path)


# ── Department-level assumptions for EOQ inputs ──────────────────────────────
DEPT_ASSUMPTIONS = {
    # dept_id: (avg_unit_price, holding_cost_rate, order_cost)
    1:  (45.0,  0.22, 150),
    2:  (38.0,  0.20, 120),
    3:  (85.0,  0.24, 180),
    4:  (120.0, 0.22, 200),
    5:  (60.0,  0.23, 160),
    6:  (95.0,  0.25, 190),
    7:  (55.0,  0.21, 140),
    8:  (30.0,  0.20, 110),
    9:  (70.0,  0.23, 155),
    10: (50.0,  0.22, 145),
}
DEFAULT_UNIT_PRICE   = 65.0
DEFAULT_HOLDING_RATE = 0.22
DEFAULT_ORDER_COST   = 160.0
AVG_UNIT_PRICE_PROXY = 35.0   # revenue → units proxy


def load_and_merge(
    train_path    = None,
    features_path = None,
    stores_path   = None,
):
    # Auto-discover files if paths not given
    train_path    = train_path    or _find_file("train")
    features_path = features_path or _find_file("features")
    stores_path   = stores_path   or _find_file("stores")

    train    = _read(train_path)
    features = _read(features_path)
    stores   = _read(stores_path)

    # Parse dates (handles DD-MM-YYYY and YYYY-MM-DD)
    train["Date"]    = pd.to_datetime(train["Date"],    format="mixed", dayfirst=True)
    features["Date"] = pd.to_datetime(features["Date"], format="mixed", dayfirst=True)

    # Normalise IsHoliday → int
    for df in [train, features]:
        col = df["IsHoliday"]
        if col.dtype == object:
            df["IsHoliday"] = col.str.upper().map({"TRUE": 1, "FALSE": 0})
        else:
            df["IsHoliday"] = col.astype(int)

    features_clean = features.drop(columns=["IsHoliday"], errors="ignore")

    md_cols = ["MarkDown1","MarkDown2","MarkDown3","MarkDown4","MarkDown5"]
    for col in md_cols:
        if col in features_clean.columns:
            features_clean[col] = pd.to_numeric(features_clean[col], errors="coerce").fillna(0)

    df = (
        train
        .merge(features_clean, on=["Store","Date"], how="left")
        .merge(stores, on="Store", how="left")
    )

    df = df[df["Weekly_Sales"] >= 0].copy()

    # Estimate weekly units from revenue
    df["Weekly_Units"] = (df["Weekly_Sales"] / AVG_UNIT_PRICE_PROXY).round(0).astype(int).clip(lower=1)

    # Attach per-dept EOQ assumptions
    df["Unit_Price"]        = df["Dept"].map(lambda d: DEPT_ASSUMPTIONS.get(d, (DEFAULT_UNIT_PRICE,))[0])
    df["Holding_Cost_Rate"] = df["Dept"].map(
        lambda d: DEPT_ASSUMPTIONS[d][1] if d in DEPT_ASSUMPTIONS else DEFAULT_HOLDING_RATE)
    df["Order_Cost"]        = df["Dept"].map(
        lambda d: DEPT_ASSUMPTIONS[d][2] if d in DEPT_ASSUMPTIONS else DEFAULT_ORDER_COST)

    # Stockout proxy: bottom-10th-pct sales per dept
    low_thresh = df.groupby("Dept")["Weekly_Sales"].transform(lambda x: x.quantile(0.10))
    df["Stockout_Flag"] = (df["Weekly_Sales"] <= low_thresh).astype(int)

    df["Total_MarkDown"] = df[md_cols].sum(axis=1)
    df["Year"]           = df["Date"].dt.year
    df["Month"]          = df["Date"].dt.month
    df["WeekOfYear"]     = df["Date"].dt.isocalendar().week.astype(int)

    df.sort_values(["Store","Dept","Date"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    print(f"Merged: {len(df):,} rows | {df['Store'].nunique()} stores | "
          f"{df['Dept'].nunique()} depts | "
          f"{df['Date'].min().date()} to {df['Date'].max().date()}")
    return df


if __name__ == "__main__":
    df = load_and_merge()
    print(df.head(3).to_string())
