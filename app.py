"""
app.py  —  Walmart Retail Inventory Optimization Dashboard
==========================================================
Real Kaggle Walmart dataset (train.csv + features.csv + stores.csv)

Run:
    streamlit run app.py

Place your 3 CSV files in:
    data/train.csv
    data/features.csv
    data/stores.csv
"""

import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_loader import load_and_merge
from inventory_optimizer import (
    aggregate_product_metrics,
    calculate_inventory_metrics,
    compute_kpis,
    weekly_demand_trend,
    eoq_sensitivity,
    calculate_safety_stock,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Walmart Inventory Optimizer",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.kpi-card {
    background: linear-gradient(135deg,#1e3a5f 0%,#2d6a9f 100%);
    padding:1.1rem 1.2rem; border-radius:12px; color:white;
    text-align:center; margin-bottom:6px;
}
.kpi-warn { background: linear-gradient(135deg,#7b2d00 0%,#c0392b 100%); }
.kpi-value { font-size:1.9rem; font-weight:700; margin:0; }
.kpi-label { font-size:0.74rem; opacity:.85; margin-top:4px; }
.sh { font-size:1rem; font-weight:600;
      border-left:4px solid #2d6a9f; padding-left:10px;
      margin:1.1rem 0 0.5rem 0; }
</style>
""", unsafe_allow_html=True)


# ── Cached data pipeline ─────────────────────────────────────────────────────
@st.cache_data(show_spinner="Merging Walmart dataset…")
def get_data(lead_time, service_level):
    df_raw = load_and_merge()
    df_agg = aggregate_product_metrics(df_raw)
    df_met = calculate_inventory_metrics(df_agg, lead_time, service_level)
    kpis   = compute_kpis(df_met)
    return df_raw, df_agg, df_met, kpis


def kpi_card(col, label, value, warn=False):
    cls = "kpi-card kpi-warn" if warn else "kpi-card"
    col.markdown(
        f'<div class="{cls}"><p class="kpi-value">{value}</p>'
        f'<p class="kpi-label">{label}</p></div>',
        unsafe_allow_html=True,
    )


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🛒 Walmart Inventory\nOptimizer")
    st.caption("Kaggle Walmart Sales Dataset")
    st.markdown("---")

    st.subheader("⚙️ Parameters")
    lead_time  = st.slider("Lead Time (weeks)", 1, 8, 2)
    svc_level  = st.selectbox(
        "Service Level", [0.90, 0.95, 0.99], index=1,
        format_func=lambda x: f"{int(x*100)}%"
    )

    # Auto-discovery handles file location — catch errors gracefully
    try:
        df_raw, df_agg, df_met, kpis = get_data(lead_time, svc_level)
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()


    st.markdown("---")
    st.subheader("🔍 Filters")

    stores = ["All"] + sorted(df_met["Store"].unique().tolist())
    sel_store = st.selectbox("Store", stores)

    store_types = ["All"] + sorted(df_met["Store_Type"].dropna().unique().tolist())
    sel_type = st.selectbox("Store Type", store_types)

    depts = ["All"] + sorted(df_met["Dept"].unique().tolist())
    sel_dept = st.selectbox("Department", depts)

    st.markdown("---")
    st.caption(
        f"Dataset: {len(df_raw):,} rows\n\n"
        f"{df_raw['Store'].nunique()} stores · "
        f"{df_raw['Dept'].nunique()} depts\n\n"
        f"{df_raw['Date'].min().date()} → {df_raw['Date'].max().date()}"
    )


# ── Apply filters ─────────────────────────────────────────────────────────────
df_f = df_met.copy()
if sel_store != "All":
    df_f = df_f[df_f["Store"] == int(sel_store)]
if sel_type != "All":
    df_f = df_f[df_f["Store_Type"] == sel_type]
if sel_dept != "All":
    df_f = df_f[df_f["Dept"] == int(sel_dept)]
kpis_f = compute_kpis(df_f)


# ── Main ──────────────────────────────────────────────────────────────────────
st.title("🛒 Walmart Retail Inventory Optimization")
st.caption("EOQ · Reorder Points · Safety Stock · Stockout Risk  |  Real Kaggle Walmart Dataset")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview", "🔬 Inventory Analysis",
    "📈 Demand Trends", "🏪 Store Intelligence", "⚗️ Sensitivity"
])


# ══════════  TAB 1: OVERVIEW  ══════════
with tab1:
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    kpi_card(c1, "Total SKUs",         kpis_f["total_skus"])
    kpi_card(c2, "Avg EOQ (units)",    int(kpis_f["avg_eoq"]))
    kpi_card(c3, "Avg Reorder Point",  int(kpis_f["avg_rop"]))
    kpi_card(c4, "Avg Safety Stock",   int(kpis_f["avg_safety_stock"]))
    kpi_card(c5, "High-Risk SKUs",     kpis_f["high_risk_skus"],  warn=kpis_f["high_risk_skus"]>0)
    kpi_card(c6, "Avg Stockout Rate",  f"{kpis_f['avg_stockout_rate']}%",
             warn=kpis_f["avg_stockout_rate"]>20)

    st.markdown("<div class='sh'>Total Revenue by Store (coloured by Store Type)</div>",
                unsafe_allow_html=True)
    rev_store = (
        df_f.groupby(["Store","Store_Type"])["Total_Revenue"]
        .sum().reset_index()
        .sort_values("Total_Revenue", ascending=False)
    )
    fig = px.bar(rev_store, x="Store", y="Total_Revenue", color="Store_Type",
                 labels={"Total_Revenue":"Revenue ($)","Store":"Store #"},
                 color_discrete_map={"A":"#2d6a9f","B":"#e07b39","C":"#27ae60"},
                 height=360)
    fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white")
    st.plotly_chart(fig, use_container_width=True)

    cl, cr = st.columns(2)
    with cl:
        st.markdown("<div class='sh'>Top 15 Depts by Avg Weekly Sales</div>",
                    unsafe_allow_html=True)
        top_dept = (
            df_f.groupby("Dept")["Avg_Weekly_Sales"].mean()
            .nlargest(15).reset_index()
        )
        fig2 = px.bar(top_dept, x="Dept", y="Avg_Weekly_Sales",
                      labels={"Avg_Weekly_Sales":"Avg Weekly Sales ($)","Dept":"Dept #"},
                      color="Avg_Weekly_Sales", color_continuous_scale="Blues", height=320)
        fig2.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                            font_color="white", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with cr:
        st.markdown("<div class='sh'>Stockout Rate by Store Type</div>",
                    unsafe_allow_html=True)
        so_type = (
            df_f.groupby("Store_Type")["Stockout_Rate_Pct"].mean()
            .reset_index()
        )
        fig3 = px.pie(so_type, names="Store_Type", values="Stockout_Rate_Pct",
                      color_discrete_sequence=["#2d6a9f","#e07b39","#27ae60"],
                      height=320)
        fig3.update_layout(paper_bgcolor="#0e1117", font_color="white")
        st.plotly_chart(fig3, use_container_width=True)


# ══════════  TAB 2: INVENTORY ANALYSIS  ══════════
with tab2:
    st.markdown("<div class='sh'>EOQ vs Safety Stock (bubble = Annual Orders, colour = Store Type)</div>",
                unsafe_allow_html=True)
    fig_b = px.scatter(
        df_f, x="EOQ", y="Safety_Stock", size="Annual_Orders",
        color="Store_Type", hover_data={"Store":True,"Dept":True,"Reorder_Point":True,
                                         "Total_Inventory_Cost":":.0f"},
        color_discrete_map={"A":"#2d6a9f","B":"#e07b39","C":"#27ae60"},
        labels={"EOQ":"EOQ (units)","Safety_Stock":"Safety Stock (units)"},
        height=430,
    )
    fig_b.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white")
    st.plotly_chart(fig_b, use_container_width=True)

    cl, cr = st.columns(2)
    with cl:
        st.markdown("<div class='sh'>Ordering vs Holding Cost Split</div>", unsafe_allow_html=True)
        cost_df = (
            df_f.groupby("Store_Type")
            .agg(Ordering=("Annual_Ordering_Cost","sum"),
                 Holding =("Annual_Holding_Cost","sum"))
            .reset_index()
            .melt(id_vars="Store_Type", var_name="Cost Type", value_name="Cost ($)")
        )
        fig_c = px.bar(cost_df, x="Store_Type", y="Cost ($)", color="Cost Type",
                        barmode="stack",
                        color_discrete_map={"Ordering":"#2d6a9f","Holding":"#e07b39"},
                        height=320)
        fig_c.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white")
        st.plotly_chart(fig_c, use_container_width=True)

    with cr:
        st.markdown("<div class='sh'>EOQ Distribution by Store Type</div>", unsafe_allow_html=True)
        fig_e = px.box(df_f, x="Store_Type", y="EOQ", color="Store_Type",
                        color_discrete_map={"A":"#2d6a9f","B":"#e07b39","C":"#27ae60"},
                        height=320)
        fig_e.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                             font_color="white", showlegend=False)
        st.plotly_chart(fig_e, use_container_width=True)

    st.markdown("<div class='sh'>📋 Inventory Metrics Table</div>", unsafe_allow_html=True)
    disp = df_f[[
        "Store","Store_Type","Store_Size","Dept","EOQ","Safety_Stock",
        "Reorder_Point","Annual_Orders","Total_Inventory_Cost","Stockout_Rate_Pct"
    ]].rename(columns={
        "Store_Type":"Type","Store_Size":"Size","Safety_Stock":"Safety Stock",
        "Reorder_Point":"Reorder Pt","Annual_Orders":"Orders/yr",
        "Total_Inventory_Cost":"Inv Cost ($)","Stockout_Rate_Pct":"Stockout %"
    }).sort_values("Stockout %", ascending=False).reset_index(drop=True)
    st.dataframe(disp, use_container_width=True, height=360)


# ══════════  TAB 3: DEMAND TRENDS  ══════════
with tab3:
    st.markdown("<div class='sh'>Weekly Demand & Sales Trend</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    t_store = c1.selectbox("Store", sorted(df_raw["Store"].unique()), key="ts")
    t_dept  = c2.selectbox("Dept",  sorted(df_raw["Dept"].unique()),  key="td")

    trend = weekly_demand_trend(df_raw, t_store, t_dept)

    fig_t = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        subplot_titles=["Weekly Units Sold + 4-Week MA",
                        "Weekly Revenue ($)", "Markdown Spend ($)"],
        row_heights=[0.45, 0.30, 0.25],
    )
    fig_t.add_trace(go.Scatter(x=trend["Date"], y=trend["Weekly_Units"],
                                name="Units", line=dict(color="#2d6a9f", width=1.2)), row=1, col=1)
    fig_t.add_trace(go.Scatter(x=trend["Date"], y=trend["Rolling_Avg"],
                                name="4-Wk MA", line=dict(color="#e07b39", width=2, dash="dot")), row=1, col=1)

    # Holiday markers
    hol = trend[trend["IsHoliday"] == 1]
    fig_t.add_trace(go.Scatter(x=hol["Date"], y=hol["Weekly_Units"],
                                mode="markers", name="Holiday",
                                marker=dict(color="red", size=7, symbol="star")), row=1, col=1)

    fig_t.add_trace(go.Bar(x=trend["Date"], y=trend["Weekly_Sales"],
                            name="Revenue", marker_color="#27ae60"), row=2, col=1)
    fig_t.add_trace(go.Bar(x=trend["Date"], y=trend["Total_MarkDown"],
                            name="MarkDown", marker_color="#9b59b6"), row=3, col=1)

    fig_t.update_layout(height=580, plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                         font_color="white", title_text=f"Store {t_store} · Dept {t_dept}",
                         showlegend=True)
    st.plotly_chart(fig_t, use_container_width=True)

    # Seasonal heatmap
    st.markdown("<div class='sh'>Monthly Sales Heatmap — All Depts (Store filtered)</div>",
                unsafe_allow_html=True)
    raw_f = df_raw[df_raw["Store"] == t_store].copy()
    heat  = (
        raw_f.assign(Year=raw_f["Date"].dt.year, Month=raw_f["Date"].dt.month)
        .groupby(["Year","Month"])["Weekly_Sales"].sum()
        .reset_index()
        .pivot(index="Year", columns="Month", values="Weekly_Sales")
    )
    mn = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    heat.columns = [mn[m-1] for m in heat.columns]
    fig_h = px.imshow(heat, color_continuous_scale="Blues",
                       labels=dict(color="Sales ($)"), height=250)
    fig_h.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white")
    st.plotly_chart(fig_h, use_container_width=True)


# ══════════  TAB 4: STORE INTELLIGENCE  ══════════
with tab4:
    st.markdown("<div class='sh'>Store Size vs Total Revenue</div>", unsafe_allow_html=True)
    store_intel = (
        df_f.groupby(["Store","Store_Type","Store_Size"])
        .agg(Revenue=("Total_Revenue","sum"),
             Avg_Stockout=("Stockout_Rate_Pct","mean"),
             Avg_EOQ=("EOQ","mean"))
        .reset_index()
    )
    fig_si = px.scatter(
        store_intel, x="Store_Size", y="Revenue",
        color="Store_Type", size="Avg_EOQ", hover_name="Store",
        hover_data={"Avg_Stockout":":.1f"},
        color_discrete_map={"A":"#2d6a9f","B":"#e07b39","C":"#27ae60"},
        labels={"Store_Size":"Store Size (sq ft)","Revenue":"Total Revenue ($)"},
        height=420,
    )
    fig_si.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white")
    st.plotly_chart(fig_si, use_container_width=True)

    cl, cr = st.columns(2)
    with cl:
        st.markdown("<div class='sh'>Holiday vs Non-Holiday Avg Weekly Sales</div>",
                    unsafe_allow_html=True)
        hol_cmp = (
            df_raw.groupby("IsHoliday")["Weekly_Sales"].mean().reset_index()
        )
        hol_cmp["IsHoliday"] = hol_cmp["IsHoliday"].map({0:"Non-Holiday",1:"Holiday"})
        fig_hc = px.bar(hol_cmp, x="IsHoliday", y="Weekly_Sales",
                         color="IsHoliday",
                         color_discrete_map={"Holiday":"#e07b39","Non-Holiday":"#2d6a9f"},
                         labels={"Weekly_Sales":"Avg Weekly Sales ($)","IsHoliday":""},
                         height=300)
        fig_hc.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                              font_color="white", showlegend=False)
        st.plotly_chart(fig_hc, use_container_width=True)

    with cr:
        st.markdown("<div class='sh'>Avg MarkDown Spend by Store Type</div>",
                    unsafe_allow_html=True)
        md_type = df_f.groupby("Store_Type")["Avg_Markdown"].mean().reset_index()
        fig_md = px.bar(md_type, x="Store_Type", y="Avg_Markdown",
                         color="Store_Type",
                         color_discrete_map={"A":"#2d6a9f","B":"#e07b39","C":"#27ae60"},
                         labels={"Avg_Markdown":"Avg MarkDown ($)","Store_Type":""},
                         height=300)
        fig_md.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                              font_color="white", showlegend=False)
        st.plotly_chart(fig_md, use_container_width=True)


# ══════════  TAB 5: SENSITIVITY  ══════════
with tab5:
    st.markdown("<div class='sh'>EOQ Sensitivity to Order Cost</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    s_demand = c1.number_input("Annual Demand (units)", value=5000, step=100)
    s_order  = c2.number_input("Base Order Cost ($)",   value=160,  step=10)
    s_hold   = c3.number_input("Holding Cost/unit/yr ($)", value=14.3, step=0.5)

    s_df = eoq_sensitivity(s_demand, s_order, s_hold)
    fig_s = px.line(s_df, x="Order_Cost", y="EOQ",
                     labels={"Order_Cost":"Order Cost ($)","EOQ":"Optimal EOQ (units)"},
                     markers=True, height=360)
    fig_s.add_vline(x=s_order, line_dash="dash", line_color="#e07b39",
                     annotation_text=f"Current (${s_order})", annotation_position="top right")
    fig_s.update_traces(line_color="#2d6a9f")
    fig_s.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white")
    st.plotly_chart(fig_s, use_container_width=True)

    st.markdown("<div class='sh'>Service Level vs Safety Stock</div>", unsafe_allow_html=True)
    sl_rows = []
    for sl in np.arange(0.80, 1.00, 0.01):
        ss = calculate_safety_stock(s_demand / 52 * 0.2, lead_time, round(sl, 2))
        sl_rows.append({"Service Level (%)": round(sl * 100, 0), "Safety Stock (units)": ss})
    sl_df = pd.DataFrame(sl_rows)
    fig_sl = px.area(sl_df, x="Service Level (%)", y="Safety Stock (units)",
                      color_discrete_sequence=["#2d6a9f"], height=320)
    fig_sl.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white")
    st.plotly_chart(fig_sl, use_container_width=True)

    st.info(
        "💡 **Key Insight:** Going from 95% → 99% service level increases safety stock by ~41%, "
        "significantly raising holding costs. Prioritize high service levels only for critical or "
        "high-margin SKUs."
    )
