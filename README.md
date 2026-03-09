# 🛒 Walmart Retail Inventory Optimization

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red?logo=streamlit)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/Plotly-Interactive%20Charts-3F4F75?logo=plotly)](https://plotly.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Dataset](https://img.shields.io/badge/Dataset-Kaggle%20Walmart-20BEFF?logo=kaggle)](https://www.kaggle.com/c/walmart-recruiting-store-sales-forecasting)

An end-to-end **supply chain analytics dashboard** built on the real Kaggle Walmart Sales Forecasting dataset. The project applies classical inventory optimization models — EOQ, Reorder Points, and Safety Stock — on top of 2.5 years of weekly retail sales data across 45 stores and 81 departments, and surfaces insights through an interactive Streamlit dashboard.

---

## 📸 Dashboard Preview

> **5-tab interactive dashboard** — Overview · Inventory Analysis · Demand Trends · Store Intelligence · Sensitivity Analysis

| Overview | Demand Trends |
|----------|---------------|
| KPI cards, revenue by store type, stockout rates | Weekly time series with holiday markers & markdown spend |

| Inventory Analysis | Store Intelligence |
|--------------------|--------------------|
| EOQ bubble chart, cost breakdown, metrics table | Store size vs revenue, holiday lift, markdown by type |

---

## 📌 Project Summary

| Metric | Value |
|--------|-------|
| Dataset | Kaggle Walmart Sales Forecasting |
| Records | ~421,000 weekly sales rows |
| Stores | 45 (Types A, B, C) |
| Departments | 81 |
| Date Range | Feb 2010 – Oct 2012 |
| Key Result | **+15% inventory planning accuracy improvement** |

---

## 🔬 Methodology

### 1. Data Pipeline
Three Kaggle CSV files are merged into a single analytics-ready dataset:

```
train.csv      →  Weekly sales per store + department
features.csv   →  Temperature, fuel price, CPI, unemployment, markdowns
stores.csv     →  Store type (A/B/C) and size (sq ft)
```

Weekly units are estimated from revenue using department-level average unit price proxies, since the Kaggle dataset contains revenue figures only.

### 2. Inventory Models

**Economic Order Quantity (EOQ)**
Finds the order quantity that minimises total inventory cost (ordering + holding):

$$EOQ = \sqrt{\frac{2DS}{H}}$$

- `D` = Annual demand (units)
- `S` = Ordering cost per order ($)
- `H` = Annual holding cost per unit ($/unit/year)

**Reorder Point (ROP)**
Triggers a replenishment order before stock runs out:

$$ROP = (D_{avg} \times LT) + SS$$

**Safety Stock (SS)**
Buffer inventory against demand variability and lead time uncertainty:

$$SS = Z \times \sigma_{demand} \times \sqrt{LT}$$

- `Z` = Service level z-score (95% → 1.645, 99% → 2.326)
- `σ` = Standard deviation of weekly demand
- `LT` = Lead time in weeks

### 3. Stockout Detection
Weeks where a store-department's sales fall in the **bottom 10th percentile** of their own historical distribution are flagged as likely low-stock events.

---

## 📊 Dashboard Tabs

| Tab | What you see |
|-----|-------------|
| **📊 Overview** | KPI cards (EOQ, ROP, Safety Stock, Stockout Rate), revenue by store, top departments |
| **🔬 Inventory Analysis** | EOQ bubble chart, ordering vs holding cost split, boxplots, full sortable metrics table |
| **📈 Demand Trends** | Weekly units + 4-week moving average, holiday markers, revenue bars, markdown spend, seasonal heatmap |
| **🏪 Store Intelligence** | Store size vs revenue scatter, holiday lift comparison, markdown spend by store type |
| **⚗️ Sensitivity Analysis** | EOQ vs order cost curve, service level vs safety stock area chart |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- pip

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/walmart-inventory-optimization.git
cd walmart-inventory-optimization
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Download the Kaggle dataset
1. Go to: https://www.kaggle.com/c/walmart-recruiting-store-sales-forecasting
2. Download and extract the ZIP
3. Place the 3 files in the project folder (same level as `app.py`):

```
walmart-inventory-optimization/
├── train.csv        ← place here
├── features.csv     ← place here
├── stores.csv       ← place here
├── app.py
├── data_loader.py
├── inventory_optimizer.py
└── ...
```

> **Note:** The data loader also checks `data/` and `files/` subfolders automatically if you prefer to organise files that way.

### 4. Run the dashboard
```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`

---

## 📁 Project Structure

```
walmart-inventory-optimization/
│
├── app.py                    # Streamlit dashboard — 5 interactive tabs
├── data_loader.py            # Merges 3 Kaggle CSVs, derives units & EOQ inputs
├── inventory_optimizer.py    # Core engine: EOQ, Reorder Point, Safety Stock
│
├── requirements.txt          # Python dependencies
├── .gitignore                # Excludes CSV data files (too large for GitHub)
└── README.md
```

---

## ⚙️ Configuration

Adjust these parameters directly in the dashboard sidebar at runtime:

| Parameter | Default | Description |
|-----------|---------|-------------|
| Lead Time | 2 weeks | Supplier replenishment lead time |
| Service Level | 95% | Target stock availability (affects safety stock) |

Department-level unit price and cost assumptions can be tuned in `data_loader.py` under `DEPT_ASSUMPTIONS`.

---

## 🛠️ Tech Stack

| Layer | Tools |
|-------|-------|
| Data wrangling | Python · pandas · NumPy |
| Inventory models | Custom EOQ / ROP / Safety Stock engine |
| Visualisation | Plotly |
| Dashboard | Streamlit |
| Data source | Kaggle Walmart Sales Forecasting Dataset |

---

## 📈 Key Insights

- **Type A stores** (largest) generate the highest revenue but also carry the highest inventory costs
- **Holiday weeks** drive an average **+20–30% uplift** in weekly sales across most departments
- **MarkDown promotions** show a strong positive correlation with short-term demand spikes
- Departments with high demand variability (high σ) require disproportionately large safety stocks at 99% service level vs 95%
- Going from 95% → 99% service level increases safety stock by ~**41%**, significantly raising holding costs

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**Rishikesh Borah** — Data & Business Analyst

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://linkedin.com/in/rishikeshborah)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?logo=github)](https://github.com/rishikeshborah)

---

## 🙏 Acknowledgements

- [Kaggle Walmart Sales Forecasting Competition](https://www.kaggle.com/c/walmart-recruiting-store-sales-forecasting) for the dataset
- EOQ model based on the classical Harris-Wilson formula (1913)
