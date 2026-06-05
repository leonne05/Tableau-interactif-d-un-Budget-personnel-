import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from pathlib import Path

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Budget Dashboard",
    page_icon="💶",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 600; }
    [data-testid="stMetricDelta"] { font-size: 0.85rem; }
    .block-container { padding-top: 1.5rem; }
    h1 { font-size: 1.6rem !important; }
</style>
""", unsafe_allow_html=True)

CATEGORY_COLORS = {
    "Logement":     "#4C72B0",
    "Alimentation": "#55A868",
    "Transport":    "#C44E52",
    "Loisirs":      "#8172B2",
    "Santé":        "#CCB974",
    "Vêtements":    "#64B5CD",
    "Épargne":      "#2D9CDB",
}

# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path: str = "data/transactions.csv") -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df["month"]      = df["date"].dt.to_period("M").dt.to_timestamp()
    df["month_label"] = df["date"].dt.strftime("%b %Y")
    df["abs_amount"] = df["amount"].abs()
    return df

df_all = load_data()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("💶 Budget Analyzer")
    st.markdown("---")

    months = sorted(df_all["month_label"].unique(),
                    key=lambda m: pd.to_datetime(m, format="%b %Y"))
    selected_months = st.multiselect(
        "Filter by month",
        options=months,
        default=months,
    )

    st.markdown("---")
    categories = sorted(df_all["category"].unique())
    selected_cats = st.multiselect(
        "Filter by category",
        options=categories,
        default=categories,
    )

    st.markdown("---")
    st.caption("💡 Tip: deselect months or categories to drill down.")

# ── Filter ─────────────────────────────────────────────────────────────────────
df = df_all[
    df_all["month_label"].isin(selected_months) &
    df_all["category"].isin(selected_cats)
]

# ── KPIs ───────────────────────────────────────────────────────────────────────
income   = df[df["type"] == "income"]["abs_amount"].sum()
expenses = df[df["type"] == "expense"]["abs_amount"].sum()
savings  = income - expenses
rate     = (savings / income * 100) if income else 0

st.title("💶 Personal Budget Dashboard")
st.caption(f"Period: {df['date'].min().date()} → {df['date'].max().date()}  |  {len(selected_months)} month(s) selected")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Income",    f"{income:,.0f} €")
c2.metric("Total Expenses",  f"{expenses:,.0f} €",  delta=f"-{expenses:,.0f} €", delta_color="inverse")
c3.metric("Net Savings",     f"{savings:,.0f} €",   delta=f"{savings:,.0f} €")
c4.metric("Savings Rate",    f"{rate:.1f} %",       delta=f"{rate:.1f} %")

st.markdown("---")

# ── Row 1 — Monthly overview + Donut ──────────────────────────────────────────
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Monthly income vs expenses")
    monthly = (
        df.groupby(["month", "month_label", "type"])["abs_amount"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
        .sort_values("month")
    )
    monthly["savings"] = monthly.get("income", 0) - monthly.get("expense", 0)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=monthly["month_label"], y=monthly.get("income", []),
        name="Income", marker_color="#55A868", opacity=0.85,
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=monthly["month_label"], y=monthly.get("expense", []),
        name="Expenses", marker_color="#C44E52", opacity=0.85,
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=monthly["month_label"], y=monthly["savings"],
        name="Savings", mode="lines+markers",
        line=dict(color="#2D9CDB", width=2.5, dash="dot"),
        marker=dict(size=7),
    ), secondary_y=True)

    fig.update_layout(
        barmode="group", height=320, margin=dict(t=10, b=10, l=0, r=0),
        legend=dict(orientation="h", y=1.12),
        yaxis=dict(ticksuffix=" €"),
        yaxis2=dict(ticksuffix=" €", showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Spending breakdown")
    exp_by_cat = (
        df[df["type"] == "expense"]
        .groupby("category")["abs_amount"]
        .sum()
        .reset_index()
        .sort_values("abs_amount", ascending=False)
    )
    colors = [CATEGORY_COLORS.get(c, "#AAAAAA") for c in exp_by_cat["category"]]
    fig2 = go.Figure(go.Pie(
        labels=exp_by_cat["category"],
        values=exp_by_cat["abs_amount"],
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="percent",
        hovertemplate="%{label}: %{value:,.0f} €<extra></extra>",
    ))
    fig2.update_layout(height=320, margin=dict(t=10, b=10, l=0, r=0),
                       showlegend=True,
                       legend=dict(orientation="v", x=1.0))
    st.plotly_chart(fig2, use_container_width=True)

# ── Row 2 — Category trend + Savings rate ─────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("Category trend over time")
    top_cats = (
        df[df["type"] == "expense"]
        .groupby("category")["abs_amount"]
        .sum()
        .nlargest(4)
        .index.tolist()
    )
    trend = (
        df[(df["type"] == "expense") & (df["category"].isin(top_cats))]
        .groupby(["month", "month_label", "category"])["abs_amount"]
        .sum()
        .reset_index()
        .sort_values("month")
    )
    fig3 = px.line(
        trend, x="month_label", y="abs_amount", color="category",
        markers=True, color_discrete_map=CATEGORY_COLORS,
        labels={"abs_amount": "€", "month_label": "", "category": "Category"},
    )
    fig3.update_layout(height=280, margin=dict(t=10, b=10, l=0, r=0),
                       yaxis=dict(ticksuffix=" €"),
                       legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("Monthly savings rate")
    monthly2 = (
        df.groupby(["month", "month_label", "type"])["abs_amount"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
        .sort_values("month")
    )
    monthly2["rate"] = (
        (monthly2.get("income", 0) - monthly2.get("expense", 0))
        / monthly2.get("income", 1) * 100
    )
    avg_rate = monthly2["rate"].mean()
    bar_colors = ["#55A868" if r >= 0 else "#C44E52" for r in monthly2["rate"]]

    fig4 = go.Figure()
    fig4.add_trace(go.Bar(
        x=monthly2["month_label"], y=monthly2["rate"],
        marker_color=bar_colors, opacity=0.85, name="Savings rate",
    ))
    fig4.add_hline(y=avg_rate, line_dash="dash", line_color="#2D9CDB",
                   annotation_text=f"Avg {avg_rate:.1f}%",
                   annotation_position="top right")
    fig4.update_layout(height=280, margin=dict(t=10, b=10, l=0, r=0),
                       yaxis=dict(ticksuffix=" %"), showlegend=False)
    st.plotly_chart(fig4, use_container_width=True)

# ── Raw data expander ──────────────────────────────────────────────────────────
with st.expander("📋 Raw transactions"):
    st.dataframe(
        df[["date", "category", "subcategory", "description", "amount", "type"]]
        .sort_values("date", ascending=False)
        .reset_index(drop=True),
        use_container_width=True,
        height=300,
    )