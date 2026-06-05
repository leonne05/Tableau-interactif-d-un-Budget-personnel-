"""
Personal Budget Analyzer
========================
A clean Python project to analyze personal finances.
Author: Data Analyst Portfolio Project
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
PALETTE = {
    "Logement":     "#4C72B0",
    "Alimentation": "#55A868",
    "Transport":    "#C44E52",
    "Loisirs":      "#8172B2",
    "Santé":        "#CCB974",
    "Vêtements":    "#64B5CD",
    "Épargne":      "#2D9CDB",
    "Autres":       "#AAAAAA",
}
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


# ── 1. Load & Clean ────────────────────────────────────────────────────────────
def load_data(filepath: str = "transactions.csv") -> pd.DataFrame:
    df = pd.read_csv(filepath, parse_dates=["date"])
    df["month"]      = df["date"].dt.to_period("M")
    df["month_name"] = df["date"].dt.strftime("%b %Y")
    df["abs_amount"] = df["amount"].abs()
    return df


# ── 2. Summary stats ───────────────────────────────────────────────────────────
def summary(df: pd.DataFrame) -> dict:
    income   = df[df["type"] == "income"]["amount"].sum()
    expenses = df[df["type"] == "expense"]["abs_amount"].sum()
    savings  = income - expenses
    rate     = savings / income * 100 if income else 0
    return dict(income=income, expenses=expenses, savings=savings, rate=rate)


def print_summary(df: pd.DataFrame):
    s = summary(df)
    months = df["month"].nunique()
    print("=" * 48)
    print("  💶  PERSONAL BUDGET — 6-MONTH SUMMARY")
    print("=" * 48)
    print(f"  Period          : {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"  Months analysed : {months}")
    print(f"  Total income    : {s['income']:>10,.2f} €")
    print(f"  Total expenses  : {s['expenses']:>10,.2f} €")
    print(f"  Net savings     : {s['savings']:>10,.2f} €")
    print(f"  Savings rate    : {s['rate']:>9.1f} %")
    print("=" * 48)

    top = (
        df[df["type"] == "expense"]
        .groupby("category")["abs_amount"]
        .sum()
        .sort_values(ascending=False)
    )
    print("\n  📊  Top spending categories")
    print("  " + "-" * 36)
    for cat, val in top.items():
        bar = "█" * int(val / top.max() * 20)
        print(f"  {cat:<15} {val:>8,.0f} €  {bar}")
    print()


# ── 3. Visualisations ──────────────────────────────────────────────────────────
def fmt_euro(x, _):
    return f"{x:,.0f} €"


def plot_monthly_overview(df: pd.DataFrame):
    """Bar chart: income vs expenses per month, line for savings."""
    monthly = (
        df.groupby(["month", "month_name", "type"])["abs_amount"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
        .sort_values("month")
    )
    monthly["savings"] = monthly.get("income", 0) - monthly.get("expense", 0)

    fig, ax1 = plt.subplots(figsize=(11, 5))
    x     = range(len(monthly))
    width = 0.35

    ax1.bar([i - width/2 for i in x], monthly["income"],  width, label="Revenus",   color="#55A868", alpha=0.85)
    ax1.bar([i + width/2 for i in x], monthly["expense"], width, label="Dépenses",  color="#C44E52", alpha=0.85)
    ax1.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_euro))
    ax1.set_ylabel("Montant (€)", fontsize=11)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(monthly["month_name"], rotation=15, ha="right")
    ax1.legend(loc="upper left")

    ax2 = ax1.twinx()
    ax2.plot(list(x), monthly["savings"], "o--", color="#2D9CDB", linewidth=2,
             markersize=7, label="Épargne nette")
    ax2.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_euro))
    ax2.set_ylabel("Épargne nette (€)", fontsize=11, color="#2D9CDB")
    ax2.tick_params(axis="y", labelcolor="#2D9CDB")
    ax2.legend(loc="upper right")

    ax1.set_title("Revenus vs Dépenses par mois", fontsize=14, fontweight="bold", pad=14)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "01_monthly_overview.png", dpi=150)
    plt.close()
    print("  ✅  01_monthly_overview.png")


def plot_expense_breakdown(df: pd.DataFrame):
    """Donut chart of expense share by category."""
    expenses = df[df["type"] == "expense"]
    by_cat   = expenses.groupby("category")["abs_amount"].sum().sort_values(ascending=False)

    colors = [PALETTE.get(c, "#AAAAAA") for c in by_cat.index]
    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, texts, autotexts = ax.pie(
        by_cat.values,
        labels=by_cat.index,
        colors=colors,
        autopct="%1.1f%%",
        pctdistance=0.82,
        startangle=140,
        wedgeprops=dict(width=0.55, edgecolor="white", linewidth=2),
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_title("Répartition des dépenses par catégorie", fontsize=14,
                 fontweight="bold", pad=20)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "02_expense_breakdown.png", dpi=150)
    plt.close()
    print("  ✅  02_expense_breakdown.png")


def plot_category_trend(df: pd.DataFrame, top_n: int = 4):
    """Line chart of top-N expense categories over months."""
    expenses = df[df["type"] == "expense"]
    top_cats = (
        expenses.groupby("category")["abs_amount"]
        .sum()
        .nlargest(top_n)
        .index.tolist()
    )
    monthly_cat = (
        expenses[expenses["category"].isin(top_cats)]
        .groupby(["month", "month_name", "category"])["abs_amount"]
        .sum()
        .reset_index()
        .sort_values("month")
    )

    fig, ax = plt.subplots(figsize=(11, 5))
    for cat in top_cats:
        sub = monthly_cat[monthly_cat["category"] == cat]
        ax.plot(sub["month_name"], sub["abs_amount"], "o-", label=cat,
                color=PALETTE.get(cat, "#AAAAAA"), linewidth=2.2, markersize=6)

    ax.yaxis.set_major_formatter(mtick.FuncFormatter(fmt_euro))
    ax.set_ylabel("Dépenses (€)", fontsize=11)
    ax.set_xlabel("")
    plt.xticks(rotation=15, ha="right")
    ax.legend(title="Catégorie", framealpha=0.9)
    ax.set_title(f"Évolution mensuelle — Top {top_n} catégories", fontsize=14,
                 fontweight="bold", pad=14)
    sns.despine()
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "03_category_trend.png", dpi=150)
    plt.close()
    print("  ✅  03_category_trend.png")


def plot_savings_rate(df: pd.DataFrame):
    """Bar chart of monthly savings rate."""
    monthly = (
        df.groupby(["month", "month_name", "type"])["abs_amount"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
        .sort_values("month")
    )
    monthly["rate"] = (monthly.get("income", 0) - monthly.get("expense", 0)) / monthly.get("income", 1) * 100
    colors = ["#55A868" if r >= 0 else "#C44E52" for r in monthly["rate"]]

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(monthly["month_name"], monthly["rate"], color=colors, alpha=0.85, edgecolor="white")
    ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
    ax.axhline(monthly["rate"].mean(), color="#2D9CDB", linewidth=1.5,
               linestyle="--", label=f"Moyenne : {monthly['rate'].mean():.1f} %")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylabel("Taux d'épargne (%)", fontsize=11)
    plt.xticks(rotation=15, ha="right")
    ax.legend()
    ax.set_title("Taux d'épargne mensuel", fontsize=14, fontweight="bold", pad=14)
    sns.despine()
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "04_savings_rate.png", dpi=150)
    plt.close()
    print("  ✅  04_savings_rate.png")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔍 Loading data …")
    df = load_data()

    print_summary(df)

    print("📈 Generating charts …")
    plot_monthly_overview(df)
    plot_expense_breakdown(df)
    plot_category_trend(df)
    plot_savings_rate(df)

    print("\n✨ All done! Charts saved in /outputs\n")
