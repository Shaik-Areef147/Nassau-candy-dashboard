"""Nassau Candy Distributor - Product Line Profitability & Margin Performance Dashboard."""
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Nassau Candy | Profitability", page_icon="🍬", layout="wide")

# ---------------------------------------------------------------- reference data
PRODUCTS = {  # product -> (division, factory)
    "Wonka Bar - Nutty Crunch Surprise": ("Chocolate", "Lot's O' Nuts"),
    "Wonka Bar - Fudge Mallows": ("Chocolate", "Lot's O' Nuts"),
    "Wonka Bar - Scrumdiddlyumptious": ("Chocolate", "Lot's O' Nuts"),
    "Wonka Bar - Milk Chocolate": ("Chocolate", "Wicked Choccy's"),
    "Wonka Bar - Triple Dazzle Caramel": ("Chocolate", "Wicked Choccy's"),
    "Laffy Taffy": ("Sugar", "Sugar Shack"),
    "SweeTARTS": ("Sugar", "Sugar Shack"),
    "Nerds": ("Sugar", "Sugar Shack"),
    "Fun Dip": ("Sugar", "Sugar Shack"),
    "Fizzy Lifting Drinks": ("Other", "Sugar Shack"),
    "Everlasting Gobstopper": ("Sugar", "Secret Factory"),
    "Hair Toffee": ("Sugar", "The Other Factory"),
    "Lickable Wallpaper": ("Other", "Secret Factory"),
    "Wonka Gum": ("Other", "Secret Factory"),
    "Kazookles": ("Other", "The Other Factory"),
}
COLS = ["Order ID", "Order Date", "Ship Date", "Ship Mode", "Division", "Region", "State/Province",
        "Product Name", "Sales", "Units", "Gross Profit", "Cost"]
ALIASES = {"orderid": "Order ID", "orderdate": "Order Date", "shipdate": "Ship Date", "shipmode": "Ship Mode",
           "division": "Division", "region": "Region", "stateprovince": "State/Province", "state": "State/Province",
           "productname": "Product Name", "product": "Product Name", "sales": "Sales", "units": "Units",
           "grossprofit": "Gross Profit", "profit": "Gross Profit", "cost": "Cost"}
PINK, TEAL, GOLD, COCOA, GREY = "#D1345B", "#1F9E89", "#E0A030", "#2B1B17", "#9AA0AE"
SEG_COLORS = {"Star": TEAL, "Niche earner": GOLD, "Volume trap": PINK, "Underperformer": GREY}

st.markdown("""
<style>
.block-container{padding-top:1.2rem;max-width:1400px}
.hero{background:linear-gradient(120deg,#2B1B17 0%,#6B2437 60%,#D1345B 130%);color:#fff;padding:26px 30px;
border-radius:16px;margin-bottom:18px}
.hero h1{color:#fff;margin:0;font-size:1.9rem}.hero p{margin:6px 0 0;color:#F3D9DF;font-size:1rem}
[data-testid="stMetric"]{background:#fff;border:1px solid #E6E8F0;border-left:5px solid #D1345B;
padding:14px 16px;border-radius:12px}
[data-testid="stMetricLabel"]{color:#5B5560}
.stTabs [data-baseweb="tab"]{font-weight:600;font-size:1rem}
.note{background:#fff;border:1px solid #E6E8F0;border-radius:12px;padding:12px 16px;margin:6px 0 14px}
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------- data layer
@st.cache_data(show_spinner=False)
def make_demo_data(seed: int = 7) -> pd.DataFrame:
    """Realistic sample data built from the Nassau product/factory mapping."""
    rng = np.random.default_rng(seed)
    price = {p: rng.uniform(1.2, 9.5) for p in PRODUCTS}
    margin = {p: rng.uniform(0.18, 0.72) for p in PRODUCTS}
    margin["Fun Dip"], margin["Laffy Taffy"], margin["Kazookles"] = 0.12, 0.2, 0.15
    states = {"East": ["New York", "Georgia", "Ohio"], "West": ["California", "Arizona", "Washington"],
              "Central": ["Illinois", "Minnesota", "Tennessee"], "South": ["Texas", "Florida", "Alabama"]}
    n, rows = 3000, []
    dates = pd.to_datetime("2023-01-01") + pd.to_timedelta(rng.integers(0, 730, n), unit="D")
    for i in range(n):
        p = list(PRODUCTS)[rng.integers(0, len(PRODUCTS))]
        u = int(rng.integers(1, 25))
        m = float(np.clip(margin[p] + rng.normal(0, 0.05), 0.02, 0.85))
        s = round(u * price[p] * rng.uniform(0.9, 1.1), 2)
        r = rng.choice(list(states))
        rows.append([f"US-{100000 + i}", dates[i], dates[i] + pd.Timedelta(days=int(rng.integers(2, 9))),
                     rng.choice(["Standard Class", "Second Class", "First Class"]), PRODUCTS[p][0], r,
                     rng.choice(states[r]), p, s, u, round(s * m, 2), round(s * (1 - m), 2)])
    return pd.DataFrame(rows, columns=COLS)


def _norm(c: str) -> str:
    return re.sub(r"[^a-z]", "", str(c).lower())


@st.cache_data(show_spinner=False)
def clean(df: pd.DataFrame):
    """Validate + standardize. Returns (clean_df, list_of_messages)."""
    log, df = [], df.copy()
    df = df.rename(columns={c: ALIASES[_norm(c)] for c in df.columns if _norm(c) in ALIASES})
    df = df.loc[:, ~df.columns.duplicated()]
    missing = [c for c in ["Product Name", "Sales"] if c not in df.columns]
    if missing:
        raise ValueError(f"Required column(s) missing: {', '.join(missing)}. Found: {', '.join(map(str, df.columns))}")
    for c in ["Sales", "Units", "Gross Profit", "Cost"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
    n0 = len(df)
    df = df[df["Product Name"].notna()].copy()
    df["Product Name"] = df["Product Name"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    df["Product Name"] = df["Product Name"].str.replace(r"Wonka Bar\s*-\s*", "Wonka Bar - ", regex=True)
    if "Division" not in df.columns:
        df["Division"] = df["Product Name"].map(lambda p: PRODUCTS.get(p, ("Other", ""))[0])
    df["Division"] = df["Division"].astype(str).str.strip().str.title().replace({"Nan": "Other"})
    if "Gross Profit" not in df.columns and "Cost" in df.columns:
        df["Gross Profit"] = df["Sales"] - df["Cost"]
    if "Cost" not in df.columns and "Gross Profit" in df.columns:
        df["Cost"] = df["Sales"] - df["Gross Profit"]
    if "Gross Profit" not in df.columns:
        raise ValueError("Need either 'Gross Profit' or 'Cost' column.")
    df["Cost"] = df["Cost"].fillna(df["Sales"] - df["Gross Profit"])
    df["Gross Profit"] = df["Gross Profit"].fillna(df["Sales"] - df["Cost"])
    if "Units" not in df.columns:
        df["Units"] = np.nan
    med = df.groupby("Product Name")["Units"].transform("median")
    n_u = int(df["Units"].isna().sum())
    df["Units"] = df["Units"].fillna(med).fillna(1).clip(lower=1)
    if n_u:
        log.append(f"Filled {n_u:,} missing unit values with the product median.")
    df = df.drop_duplicates()
    bad = df["Sales"].isna() | (df["Sales"] <= 0) | df["Gross Profit"].isna() | df["Cost"].lt(0)
    if bad.sum():
        log.append(f"Removed {int(bad.sum()):,} rows with zero/invalid sales, cost or profit.")
    df = df[~bad]
    for c in ["Order Date", "Ship Date"]:
        if c in df.columns:
            d = pd.to_datetime(df[c], format="%d-%m-%Y", errors="coerce")  # dataset uses dd-mm-yyyy
            if d.isna().mean() > 0.5:
                d = pd.to_datetime(df[c], errors="coerce", dayfirst=True)
            df[c] = d
        else:
            df[c] = pd.NaT
    for c in ["Region", "State/Province", "Ship Mode", "Order ID"]:
        if c not in df.columns:
            df[c] = "Unknown"
    df["Factory"] = df["Product Name"].map(lambda p: PRODUCTS.get(p, ("", "Unknown"))[1])
    if len(df) == 0:
        raise ValueError("No valid rows left after cleaning.")
    log.append(f"{len(df):,} valid rows kept out of {n0:,}.")
    return df.reset_index(drop=True), log


def product_table(df: pd.DataFrame, thr: float) -> pd.DataFrame:
    g = df.groupby(["Product Name", "Division"], as_index=False).agg(
        Sales=("Sales", "sum"), Profit=("Gross Profit", "sum"), Cost=("Cost", "sum"), Units=("Units", "sum"))
    g["Margin %"] = np.where(g["Sales"] > 0, g["Profit"] / g["Sales"] * 100, 0.0)
    g["Profit/Unit"] = np.where(g["Units"] > 0, g["Profit"] / g["Units"], 0.0)
    g["Revenue Share %"] = g["Sales"] / g["Sales"].sum() * 100
    g["Profit Share %"] = g["Profit"] / g["Profit"].sum() * 100 if g["Profit"].sum() else 0.0
    if df["Order Date"].notna().any():
        mo = df.dropna(subset=["Order Date"]).assign(M=lambda d: d["Order Date"].dt.to_period("M"))
        mm = mo.groupby(["Product Name", "M"]).agg(s=("Sales", "sum"), p=("Gross Profit", "sum"))
        mm["m"] = mm["p"] / mm["s"] * 100
        vol = mm.groupby("Product Name")["m"].std().rename("Margin Volatility")
        g = g.merge(vol, on="Product Name", how="left")
    else:
        g["Margin Volatility"] = np.nan
    g["Margin Volatility"] = g["Margin Volatility"].fillna(0.0)
    hi_sales = g["Sales"] >= g["Sales"].median()
    ok = g["Margin %"] >= thr
    g["Segment"] = np.select([hi_sales & ok, ~hi_sales & ok, hi_sales & ~ok],
                             ["Star", "Niche earner", "Volume trap"], "Underperformer")
    g["Action"] = np.select(
        [g["Margin %"] >= thr, (g["Margin %"] < thr / 2) & ~hi_sales, hi_sales],
        ["Healthy", "Discontinuation review", "Repricing"], "Cost renegotiation")
    return g.sort_values("Profit", ascending=False).reset_index(drop=True)


def pareto(g: pd.DataFrame, col: str):
    s = g[["Product Name", col]].sort_values(col, ascending=False).reset_index(drop=True)
    tot = s[col].sum()
    s["Cum %"] = s[col].cumsum() / tot * 100 if tot else 0.0
    n80 = int((s["Cum %"] < 80).sum() + 1)
    return s, min(n80, len(s))


def style(fig, h=420):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=50, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color=COCOA), legend_title_text="")
    return fig


# ---------------------------------------------------------------- sidebar: data source
DATA_FILE = Path(__file__).parent / "data" / "Nassau_Candy_Distributor.csv"
st.sidebar.header("📂 Data")
up = st.sidebar.file_uploader("Use a different CSV (optional)", type=["csv"],
                              help="By default the dashboard reads data/Nassau_Candy_Distributor.csv.")
try:
    if up is not None:
        raw, src = pd.read_csv(up, encoding="latin-1"), f"Uploaded file: {up.name}"
    elif DATA_FILE.exists():
        raw, src = pd.read_csv(DATA_FILE, encoding="latin-1"), "Source: Nassau_Candy_Distributor.csv"
    else:
        raw, src = make_demo_data(), "Sample data (data/Nassau_Candy_Distributor.csv not found)"
    data, log = clean(raw)
except Exception as e:  # friendly error instead of a crash
    st.error(f"Could not load the data. {e}")
    st.stop()

st.markdown(f'<div class="hero"><h1>🍬 Nassau Candy Profitability Dashboard</h1>'
            f'<p>Which products and divisions really earn money, and where margin is at risk.</p></div>',
            unsafe_allow_html=True)
st.caption(src)

# ---------------------------------------------------------------- sidebar: filters
st.sidebar.header("🎛️ Filters")
dmin, dmax = data["Order Date"].min(), data["Order Date"].max()
f = data
if pd.notna(dmin):
    sel = st.sidebar.date_input("Order date range", value=(dmin.date(), dmax.date()),
                                min_value=dmin.date(), max_value=dmax.date())
    if isinstance(sel, (tuple, list)) and len(sel) == 2:
        f = f[(f["Order Date"] >= pd.Timestamp(sel[0])) & (f["Order Date"] <= pd.Timestamp(sel[1]) + pd.Timedelta(days=1))]
divs = sorted(data["Division"].unique())
chosen = st.sidebar.multiselect("Division", divs, default=divs)
f = f[f["Division"].isin(chosen)]
thr = st.sidebar.slider("Margin threshold (%)", 0, 80, 55, help="Products below this margin are flagged as risk.")
q = st.sidebar.text_input("Search product", placeholder="e.g. Wonka")
if q.strip():
    f = f[f["Product Name"].str.contains(q.strip(), case=False, regex=False)]
if f.empty:
    st.warning("No orders match the current filters. Widen the date range, pick more divisions or clear the search.")
    st.stop()
with st.sidebar.expander("Data cleaning report"):
    for m in log:
        st.write("•", m)

P = product_table(f, thr)
tot_s, tot_p = f["Sales"].sum(), f["Gross Profit"].sum()
k = st.columns(5)
k[0].metric("Total sales", f"${tot_s:,.0f}")
k[1].metric("Gross profit", f"${tot_p:,.0f}")
k[2].metric("Gross margin", f"{tot_p / tot_s * 100:.1f}%")
k[3].metric("Profit per unit", f"${tot_p / f['Units'].sum():,.2f}")
k[4].metric("Products at risk", f"{int((P['Margin %'] < thr).sum())} / {len(P)}")
st.write("")

t1, t2, t3, t4, t5 = st.tabs(["📦 Product Overview", "🏭 Division Performance", "🔍 Cost vs Margin",
                              "📈 Profit Concentration", "🗂️ Data & Export"])

with t1:
    c1, c2 = st.columns(2)
    top = P.sort_values("Margin %", ascending=True)
    fig = px.bar(top, x="Margin %", y="Product Name", orientation="h", color="Margin %",
                 color_continuous_scale=["#D1345B", "#E0A030", "#1F9E89"], title="Margin leaderboard")
    fig.add_vline(x=thr, line_dash="dash", line_color=COCOA, annotation_text=f"Threshold {thr}%")
    c1.plotly_chart(style(fig, 480), use_container_width=True)
    fig = px.bar(P.sort_values("Profit"), x="Profit", y="Product Name", orientation="h", color="Division",
                 title="Profit contribution by product")
    c2.plotly_chart(style(fig, 480), use_container_width=True)
    fig = px.scatter(P, x="Sales", y="Margin %", size="Profit", color="Segment", hover_name="Product Name",
                     color_discrete_map=SEG_COLORS, size_max=45, title="Sales vs margin: who earns their shelf space?")
    fig.add_hline(y=thr, line_dash="dash", line_color=COCOA)
    fig.add_vline(x=P["Sales"].median(), line_dash="dot", line_color=GREY)
    st.plotly_chart(style(fig, 460), use_container_width=True)
    show = P[["Product Name", "Division", "Sales", "Profit", "Margin %", "Profit/Unit", "Revenue Share %",
              "Profit Share %", "Margin Volatility", "Segment"]]
    st.dataframe(show.style.format({"Sales": "${:,.0f}", "Profit": "${:,.0f}", "Margin %": "{:.1f}",
                 "Profit/Unit": "${:.2f}", "Revenue Share %": "{:.1f}", "Profit Share %": "{:.1f}",
                 "Margin Volatility": "{:.2f}"}), use_container_width=True, hide_index=True)

with t2:
    D = f.groupby("Division", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Gross Profit", "sum"),
                                                  Cost=("Cost", "sum"))
    D["Margin %"] = D["Profit"] / D["Sales"] * 100
    D["Revenue Share %"] = D["Sales"] / D["Sales"].sum() * 100
    D["Profit Share %"] = D["Profit"] / D["Profit"].sum() * 100
    D["Imbalance (pp)"] = D["Profit Share %"] - D["Revenue Share %"]
    c1, c2 = st.columns(2)
    m = D.melt(id_vars="Division", value_vars=["Sales", "Profit"], var_name="Metric", value_name="USD")
    c1.plotly_chart(style(px.bar(m, x="Division", y="USD", color="Metric", barmode="group",
                    color_discrete_map={"Sales": COCOA, "Profit": PINK}, title="Revenue vs profit"), 400),
                    use_container_width=True)
    c2.plotly_chart(style(px.box(f.assign(M=f["Gross Profit"] / f["Sales"] * 100), x="Division", y="M",
                    color="Division", title="Order-level margin distribution", labels={"M": "Margin %"}), 400),
                    use_container_width=True)
    st.dataframe(D.style.format({"Sales": "${:,.0f}", "Profit": "${:,.0f}", "Cost": "${:,.0f}", "Margin %": "{:.1f}",
                 "Revenue Share %": "{:.1f}", "Profit Share %": "{:.1f}", "Imbalance (pp)": "{:+.1f}"}),
                 use_container_width=True, hide_index=True)
    weak = D[D["Imbalance (pp)"] < -2]["Division"].tolist()
    best = D.sort_values("Margin %").iloc[-1]
    st.markdown(f'<div class="note"><b>Reading this:</b> {best["Division"]} has the strongest margin '
                f'({best["Margin %"]:.1f}%). ' + (f'Divisions taking more revenue share than profit share: '
                f'<b>{", ".join(weak)}</b>.' if weak else 'No division has a major revenue-vs-profit imbalance.')
                + '</div>', unsafe_allow_html=True)

with t3:
    fig = px.scatter(P, x="Cost", y="Sales", color="Segment", size="Units", hover_name="Product Name",
                     color_discrete_map=SEG_COLORS, size_max=40, title="Cost vs sales (above the line = profitable)")
    mx = float(max(P["Cost"].max(), P["Sales"].max()))
    fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", name="Break-even",
                             line=dict(color=COCOA, dash="dash")))
    st.plotly_chart(style(fig, 460), use_container_width=True)
    risk = P[P["Margin %"] < thr][["Product Name", "Division", "Sales", "Cost", "Margin %", "Profit/Unit",
                                   "Segment", "Action"]]
    st.subheader("Margin risk flags")
    if risk.empty:
        st.success(f"Every product meets the {thr}% margin threshold.")
    else:
        st.dataframe(risk.style.format({"Sales": "${:,.0f}", "Cost": "${:,.0f}", "Margin %": "{:.1f}",
                     "Profit/Unit": "${:.2f}"}), use_container_width=True, hide_index=True)

with t4:
    ps, n_p = pareto(P, "Profit")
    rs, n_r = pareto(P, "Sales")
    a, b, c = st.columns(3)
    a.metric("Products for 80% of revenue", f"{n_r} of {len(P)}", f"{n_r / len(P) * 100:.0f}% of range", delta_color="off")
    b.metric("Products for 80% of profit", f"{n_p} of {len(P)}", f"{n_p / len(P) * 100:.0f}% of range", delta_color="off")
    c.metric("Top product profit share", f"{P['Profit Share %'].max():.1f}%")
    for s_, ttl, col in [(ps, "Profit Pareto", "Profit"), (rs, "Revenue Pareto", "Sales")]:
        fig = go.Figure()
        fig.add_bar(x=s_["Product Name"], y=s_[col], name=col, marker_color=PINK if col == "Profit" else COCOA)
        fig.add_scatter(x=s_["Product Name"], y=s_["Cum %"], name="Cumulative %", yaxis="y2",
                        line=dict(color=TEAL, width=3))
        fig.add_hline(y=80, line_dash="dash", line_color=GREY, yref="y2")
        fig.update_layout(title=ttl, yaxis2=dict(overlaying="y", side="right", range=[0, 105], title="Cumulative %"))
        st.plotly_chart(style(fig, 400), use_container_width=True)
    dep = P["Profit Share %"].head(3).sum()
    lvl = "HIGH" if dep > 60 else "MODERATE" if dep > 40 else "LOW"
    st.markdown(f'<div class="note"><b>Dependency indicator: {lvl}</b>. The top 3 products generate '
                f'{dep:.1f}% of gross profit.</div>', unsafe_allow_html=True)

with t5:
    st.dataframe(f.head(1000), use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download product analysis (CSV)", P.to_csv(index=False).encode("utf-8"),
                       file_name="product_profitability.csv", mime="text/csv")
    st.download_button("⬇️ Download filtered data (CSV)", f.to_csv(index=False).encode("utf-8"),
                       file_name="filtered_orders.csv", mime="text/csv")
