# 🛡️ ChainCatch — SIH 2026 Prototype

<div align="center">
  <a href="https://chaincatch-sih-2026.vercel.app">
    <img src="https://img.shields.io/badge/🔴_LIVE_DEMO-Click_Here-blue?style=for-the-badge" alt="Live Demo" />
  </a>
  <p><i>Team CryptoKnights | Problem Statement 26183</i></p>
</div>

Accessible crypto tracing & VASP identification. **DEMO MODE by default — fully offline, no internet or blockchain API keys required.** LIVE MODE adds real Etherscan / TRONSCAN connectivity on top, without touching the guaranteed offline demo.

## 🚀 Live Deployment
This prototype is fully deployed to the cloud. You do not need to install anything to test it.
- **Frontend (Web App):** Hosted on Vercel.
- **Backend (API):** Hosted on Render.

👉 **[Access the Live Web Application Here](https://chaincatch-sih-2026.vercel.app)** 👈

---

## 💻 Local Project Structure

```text
chaincatch/
  backend/
    requirements.txt
    .env.example         copy to .env and fill in your keys
    .gitignore
    app/
      main.py             FastAPI routes (analyze / demo-cases / status / report)
      engine.py            demo tracing, layout, clustering, explainable risk scoring
      dataset.py            3 pre-indexed demo cases + synthetic VASP registry
      report.py              PDF investigation report generator
      config.py                LIVE MODE settings (.env loader)
      cache.py                   simple TTL file cache for live lookups
      live_tracing.py              bounded multi-hop tracing over REAL transactions
      blockchain/
        base.py                     shared exceptions, address validation, NormalizedTx
        etherscan.py                 Etherscan API V2 adapter (Ethereum)
        tronscan.py                   TRONSCAN adapter (TRON)
  frontend/
    index.html            the entire UI (React, vendored locally — no CDN, no build step)
    vendor/                react.js, react-dom.js, babel.js (bundled, offline)
```

## 🛠️ 1. Run the backend locally

```bash
cd chaincatch/backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Leave this running. Verify it's up: open http://127.0.0.1:8000/api/health — should show `{"status":"ok","mode":"DEMO"}`.

## 🌐 2. Run the frontend locally

In a second terminal:

```bash
cd chaincatch/frontend
python3 -m http.server 8080
```

Open **http://127.0.0.1:8080/index.html** in a browser.

(The frontend is a single static HTML file with React/Babel vendored locally in `vendor/`, so this also works by double-clicking `index.html` directly in most browsers — the http.server step is just the safest option in case your browser blocks `fetch()` from a `file://` page.)

## 🔍 3. Demo it (DEMO MODE — always works, no setup needed)

- Click one of the 3 demo case cards, **or** type any wallet address and click **ANALYZE WALLET** (unknown addresses get a deterministic synthetic trace — same input always reproduces the same result, no network needed).
- Explore the transaction graph (scroll to zoom, drag to pan, click nodes/edges).
- Expand the risk score to see the weighted signal breakdown.
- Click **GENERATE INVESTIGATION REPORT** to download a PDF.

### Sample wallets

| Case | Wallet | Flow |
|---|---|---|
| 1 | `0x7a3fdemo1suspectwallet0000000000000001` | ETH multi-hop -> VASP-IND-04 |
| 2 | `0x9f1edemo2suspectwallet0000000000000002` | ETH -> Bridge -> TRON -> VASP-IND-07 |
| 3 | `0x5c6edemo3suspectwallet0000000000000003` | High-risk 4-wallet cluster -> VASP-IND-11 |

Any other string (e.g. `0xdeadbeef1234`) -> synthetic deterministic trace.

## ⚡ 4. Set up LIVE MODE (optional — real Etherscan / TRONSCAN data)

```bash
cd chaincatch/backend
cp .env.example .env
```

Edit `.env`:

```
ETHERSCAN_API_KEY=your_key_here
TRONSCAN_API_KEY=                # optional — TRONSCAN works keyless at a lower rate limit
MAX_HOPS=4
MAX_WALLETS=100
MAX_TRANSACTIONS_PER_WALLET=100
CACHE_TTL_SECONDS=300
REQUEST_TIMEOUT_SECONDS=10
```

**Where to get an Etherscan API key:**
1. Sign up at https://etherscan.io/register
2. Create a key at https://etherscan.io/apidashboard
3. This one key works across Etherscan's unified **API V2** (the endpoint this project calls: `https://api.etherscan.io/v2/api?chainid=1&...`). The old per-chain V1 endpoints (`api.etherscan.io/api` with no `chainid`) were deprecated on 15 Aug 2025 — this adapter already targets the current V2 format.

**Where to get a TRONSCAN key (optional):** see https://docs.tronscan.org/ — not required to demo LIVE MODE on TRON, just raises the rate limit.

Restart the backend (`uvicorn app.main:app --port 8000`) after editing `.env`.

In the UI, click the **LIVE** toggle in the top bar, pick a chain, paste a real wallet address, and click **ANALYZE WALLET**. The BLOCKCHAIN API STATUS panel shows whether each key is configured before you even try.

If the live call fails for any reason (no key, rate limit, timeout, invalid address, no transactions), you'll see a **LIVE DATA UNAVAILABLE** banner with the reason and a **Switch to Demo Case** button — the app never crashes and DEMO MODE is always one click away.

## 📋 Notes

- All DEMO MODE wallet addresses, tx hashes, and the VASP registry are **synthetic**, clearly labelled "Demo VASP Intelligence Dataset" in the UI and PDF report. That registry is never claimed to contain real exchange addresses, in DEMO or LIVE MODE — a real wallet matching it is not expected.
- Risk scoring (both modes) is a transparent weighted sum over 7 explainable signals (see `engine.py::score_risk` / `dataset.py::RISK_WEIGHTS` for DEMO, `live_tracing.py::_derive_signals` for LIVE) — never a random number.
- LIVE MODE tracing is bounded (`MAX_HOPS` / `MAX_WALLETS` / `MAX_TRANSACTIONS_PER_WALLET` in `.env`) and cached (`CACHE_TTL_SECONDS`) — see `live_tracing.py` and `cache.py`. It never crawls unbounded or crashes the app on API failure; see `blockchain/base.py`'s exception hierarchy and `main.py::_analyze_live`.
