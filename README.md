# DeFi Money Market Yield Monitor

A Python tool that tracks and compares supply APY, TVL and rate spreads across major DeFi money market protocols, using the DeFiLlama API (free, no key required) and Dune Analytics.

---

## Overview

This project fetches historical yield data for stablecoin lending markets and produces a multi-panel interactive dashboard. The central analytical question is straightforward: how do DeFi lending rates behave relative to the Sky DSR, the closest available proxy for a risk-free rate in decentralized finance, and what does that spread tell us about capital allocation dynamics across protocols?

Metrics tracked:
- Historical supply APY per protocol, with 4-week rolling average
- Current APY versus TVL — visualizing the liquidity and yield trade-off
- APY spread relative to Sky DSR, expressed in basis points
- Summary table: current rate, 30-day average, 30-day maximum, TVL

---

## Protocols tracked

| Protocol | Asset | Mechanism |
|---|---|---|
| Aave v3 | USDC / USDT | Overcollateralized lending pool |
| Sky (MakerDAO) DSR | DAI / USDS | Protocol savings rate — benchmark |
| Compound v3 | USDC | Overcollateralized lending pool |
| Morpho | USDC | Peer-to-peer optimized lending on Aave / Compound |

---

## Getting started

```bash
# Clone the repository
git clone https://github.com/pauljoder/defi-yield-monitor.git
cd defi-yield-monitor

# Install dependencies
pip install -r requirements.txt

# Run the analysis
# DeFiLlama API is free — no key needed
python defi_yield_monitor.py

# Open defi_yield_dashboard.html in any browser
```

---

## Project structure

```
defi-yield-monitor/
├── defi_yield_monitor.py       # Main script
├── defi_yield_dashboard.html   # Output dashboard
├── requirements.txt
└── README.md
```

---

## Dashboard

The output dashboard includes four panels:

1. Supply APY over time — 4-week rolling average across all protocols
2. APY vs TVL scatter — bubble size proportional to TVL, illustrating the yield and liquidity trade-off
3. Spread vs Sky DSR — excess yield in basis points over time, per protocol
4. Summary table — current APY, 30-day average, 30-day maximum, TVL

---

## Key observations (Q1 2026)

The Sky DSR currently functions as a yield floor for stablecoin strategies — major lending protocols trade consistently within a narrow band above it. Morpho offers the highest supply APY for USDC through peer-to-peer matching, at the cost of lower liquidity depth. Aave maintains the largest TVL, reflecting a preference for liquidity certainty over marginal yield optimization. Rate compression since late 2024 closely tracks the broader monetary policy cycle, confirming that DeFi money markets are increasingly correlated with traditional interest rate dynamics.

---

## Data sources

- [DeFiLlama Yields API](https://yields.llama.fi) — free, no authentication required
- [Dune Analytics](https://dune.com) — on-chain rate history
- [Sky.money](https://sky.money) — DSR documentation

---

*Personal project — M1 Data Science (History & Culture), Universite Paris 1 Pantheon-Sorbonne*
