"""
DeFi Money Market Yield Monitor
================================
Tracks and compares lending/borrowing rates across major DeFi money market
protocols using Dune Analytics and the DeFiLlama API.

Protocols: Aave v3, Sky (MakerDAO/DSR), Compound v3, Morpho, Euler
Metrics:   Supply APY, Borrow APY, TVL, utilisation rate

Author: Paul Joder
"""

import os
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Config ────────────────────────────────────────────────────────────────────

DUNE_API_KEY  = os.getenv("DUNE_API_KEY", "YOUR_API_KEY_HERE")
DUNE_HEADERS  = {"X-Dune-API-Key": DUNE_API_KEY}
DUNE_BASE     = "https://api.dune.com/api/v1"
LLAMA_BASE    = "https://yields.llama.fi"

LLAMA_POOLS = {
    "Aave v3 — USDC (Ethereum)":  "aa70268e-4b52-42bf-a116-608b370f9501",
    "Aave v3 — USDT (Ethereum)":  "30b07df4-73de-4c48-84e2-34d2a1fbb68b",
    "Compound v3 — USDC":         "4c1a97bf-f020-4ba3-b68f-0f11c7f5f9be",
    "Morpho — USDC (Ethereum)":   "cf60f6e1-e4e3-4e4e-a451-e8513a6e6b1e",
    "Sky DSR — DAI/USDS":         "c8a24fee-ec00-4f38-86c0-9f6daebc4225",
}


# ── DeFiLlama API ──────────────────────────────────────────────────────────────

def fetch_llama_pool(pool_id: str) -> pd.DataFrame:
    url = f"{LLAMA_BASE}/chart/{pool_id}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    df = pd.DataFrame(r.json()["data"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df[["timestamp", "apy", "tvlUsd"]].rename(
        columns={"timestamp": "date", "apy": "supply_apy", "tvlUsd": "tvl_usd"}
    )


def fetch_all_llama_pools() -> dict:
    results = {}
    for name, pool_id in LLAMA_POOLS.items():
        try:
            results[name] = fetch_llama_pool(pool_id)
            print(f"  OK {name}")
        except Exception as e:
            print(f"  FAIL {name} — {e}. Using mock data.")
            results[name] = None

    mock = load_mock_data()
    for name in results:
        if results[name] is None:
            results[name] = mock.get(name, pd.DataFrame())
    return results


# ── Mock data ─────────────────────────────────────────────────────────────────

def load_mock_data() -> dict:
    import numpy as np
    dates = pd.date_range("2023-01-01", "2026-03-01", freq="W")
    n = len(dates)
    np.random.seed(42)

    def rate_series(base, noise=0.3):
        rates = [base]
        for _ in range(n - 1):
            shock = np.random.normal(0, noise)
            new_rate = rates[-1] * 0.97 + base * 0.03 + shock
            rates.append(max(0.1, new_rate))
        return rates

    rate_profiles = {
        "Aave v3 — USDC (Ethereum)":  (4.8, 0.4),
        "Aave v3 — USDT (Ethereum)":  (4.6, 0.4),
        "Compound v3 — USDC":         (4.5, 0.45),
        "Morpho — USDC (Ethereum)":   (5.1, 0.5),
        "Sky DSR — DAI/USDS":         (5.0, 0.3),
    }

    results = {}
    for name, (base, noise) in rate_profiles.items():
        supply_apy = rate_series(base, noise)
        tvl_base = {"Aave v3 — USDC (Ethereum)": 3e9, "Sky DSR — DAI/USDS": 2e9}.get(name, 8e8)
        results[name] = pd.DataFrame({
            "date":       dates,
            "supply_apy": supply_apy,
            "tvl_usd":    [tvl_base * (1 + np.random.normal(0, 0.05)) for _ in range(n)],
        })
    return results


# ── Analysis ──────────────────────────────────────────────────────────────────

def compute_stats(data: dict) -> pd.DataFrame:
    rows = []
    for name, df in data.items():
        if df.empty:
            continue
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        if df["date"].dt.tz is not None:
            df["date"] = df["date"].dt.tz_localize(None)
        recent = df[df["date"] >= df["date"].max() - pd.Timedelta(days=30)]
        rows.append({
            "Protocol":        name,
            "Current APY (%)": round(df["supply_apy"].iloc[-1], 2),
            "30d Avg APY (%)": round(recent["supply_apy"].mean(), 2),
            "30d Max APY (%)": round(recent["supply_apy"].max(), 2),
            "TVL (USD M)":     round(df["tvl_usd"].iloc[-1] / 1e6, 1),
        })
    return pd.DataFrame(rows).sort_values("Current APY (%)", ascending=False)


def spread_analysis(data: dict) -> pd.DataFrame:
    dsr = data.get("Sky DSR — DAI/USDS")
    if dsr is None or dsr.empty:
        return pd.DataFrame()

    def clean(df):
        d = df.set_index("date")["supply_apy"].copy()
        d.index = pd.to_datetime(d.index)
        if d.index.tz is not None:
            d.index = d.index.tz_localize(None)
        return d.resample("W").mean()

    dsr_series = clean(dsr).rename("DSR")
    result = pd.DataFrame(dsr_series)

    for k, v in data.items():
        if k != "Sky DSR — DAI/USDS" and not v.empty:
            s = clean(v).rename(k)
            result = result.join(s, how="inner")

    for col in result.columns[1:]:
        result[f"spread_{col}"] = result[col] - result["DSR"]

    return result


# ── Dashboard ─────────────────────────────────────────────────────────────────

def build_dashboard(data: dict) -> go.Figure:
    COLORS = px.colors.qualitative.Plotly

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Supply APY over Time — All Protocols (%)",
            "Current APY vs TVL — Snapshot",
            "APY Spread vs Sky DSR (basis points)",
            "Protocol Summary Table",
        ),
        specs=[
            [{"type": "scatter"}, {"type": "scatter"}],
            [{"type": "scatter"}, {"type": "table"}],
        ],
        vertical_spacing=0.18,
        horizontal_spacing=0.1,
    )

    # Panel 1 — APY lines
    for i, (name, df) in enumerate(data.items()):
        if df.empty:
            continue
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        if df["date"].dt.tz is not None:
            df["date"] = df["date"].dt.tz_localize(None)
        fig.add_trace(
            go.Scatter(
                x=df["date"], y=df["supply_apy"].rolling(4).mean(),
                mode="lines", name=name,
                line=dict(color=COLORS[i % len(COLORS)], width=1.8),
            ),
            row=1, col=1,
        )

    # Panel 2 — APY vs TVL bubble
    stats = compute_stats(data)
    fig.add_trace(
        go.Scatter(
            x=stats["TVL (USD M)"],
            y=stats["Current APY (%)"],
            mode="markers+text",
            text=stats["Protocol"].str.split("—").str[0].str.strip(),
            textposition="top center",
            marker=dict(
                size=stats["TVL (USD M)"].apply(lambda v: max(10, v / 80)),
                color=COLORS[:len(stats)],
                opacity=0.8,
            ),
            showlegend=False,
        ),
        row=1, col=2,
    )

    # Panel 3 — spread vs DSR
    spreads = spread_analysis(data)
    if not spreads.empty:
        spread_cols = [c for c in spreads.columns if c.startswith("spread_")]
        for i, col in enumerate(spread_cols):
            label = col.replace("spread_", "").split("—")[0].strip()
            fig.add_trace(
                go.Scatter(
                    x=spreads.index,
                    y=(spreads[col] * 100).rolling(4).mean(),
                    mode="lines", name=f"vs DSR: {label}",
                    line=dict(color=COLORS[i % len(COLORS)], width=1.5),
                    showlegend=False,
                ),
                row=2, col=1,
            )
        fig.add_hline(y=0, line_dash="dash", line_color="grey", row=2, col=1)

    # Panel 4 — summary table
    fig.add_trace(
        go.Table(
            header=dict(
                values=list(stats.columns),
                fill_color="#3B82F6",
                font=dict(color="white", size=11),
                align="left",
            ),
            cells=dict(
                values=[stats[c] for c in stats.columns],
                fill_color=[["#f8fafc", "#f1f5f9"] * len(stats)],
                align="left",
                font=dict(size=10),
            ),
        ),
        row=2, col=2,
    )

    fig.update_layout(
        title=dict(
            text="DeFi Money Market Yield Monitor — Aave · Sky DSR · Compound · Morpho",
            font=dict(size=17),
        ),
        height=780,
        template="plotly_white",
        legend=dict(orientation="h", y=-0.08, x=0),
        margin=dict(t=80, b=80, l=60, r=40),
    )
    return fig


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print("=== DeFi Money Market Yield Monitor ===\n")
    print("Fetching pool data from DeFiLlama...")
    data = fetch_all_llama_pools()

    print("\nCurrent Rates Summary:")
    stats = compute_stats(data)
    print(stats.to_string(index=False))

    print("\nBuilding dashboard...")
    fig = build_dashboard(data)
    fig.write_html("defi_yield_dashboard.html")
    print("Dashboard saved -> defi_yield_dashboard.html")


if __name__ == "__main__":
    main()
