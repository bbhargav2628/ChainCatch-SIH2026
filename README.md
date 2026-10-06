# ChainCatch: SIH 2026 Prototype

<div align="center">
  <a href="https://chaincatch-sih-2026.vercel.app">
    <img src="https://img.shields.io/badge/🔴_LIVE_DEMO-Click_Here-blue?style=for-the-badge" alt="Live Demo" />
  </a>
  <p><i>Team CryptoKnights | Problem Statement 26183</i></p>
</div>

ChainCatch makes crypto tracing and VASP identification accessible to the people who need it.

It runs in **DEMO MODE by default**, fully offline, with no internet connection and no blockchain API keys. **LIVE MODE** adds real Etherscan and TRONSCAN connectivity on top of that, and it never interferes with the guaranteed offline demo.

## Live Deployment

The prototype is already deployed, so you can try it without installing anything.

- **Frontend (web app):** hosted on Vercel
- **Backend (API):** hosted on Render

**[Open the live web application](https://chaincatch-sih-2026.vercel.app)**

---

## Local Project Structure

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

## 1. Run the backend locally

```bash
cd chaincatch/backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Keep this terminal running. To confirm the server is up, open http://127.0.0.1:8000/api/health. You should see `{"status":"ok","mode":"DEMO"}`.

## 2. Run the frontend locally

Open a second terminal and run:

```bash
cd chaincatch/frontend
python3 -m http.server 8080
```

Then open **http://127.0.0.1:8080/index.html** in your browser.

The frontend is a single static HTML file, with React and Babel vendored locally in `vendor/`. In most browsers you can also just double-click `index.html`. The `http.server` step is the safer route, since some browsers block `fetch()` calls from a `file://` page.

## 3. Try the demo (DEMO MODE: always works, no setup)

- Click one of the 3 demo case cards, **or** type any wallet address and click **ANALYZE WALLET**. Unknown addresses get a deterministic synthetic trace: the same input always produces the same result, and no network is needed.
- Explore the transaction graph. Scroll to zoom, drag to pan, and click nodes or edges for details.
- Expand the risk score to see the weighted signal breakdown.
- Click **GENERATE INVESTIGATION REPORT** to download a PDF.

### Sample wallets

| Case | Wallet | Flow |
|---|---|---|
| 1 | `0x7a3fdemo1suspectwallet0000000000000001` | ETH multi-hop -> VASP-IND-04 |
| 2 | `0x9f1edemo2suspectwallet0000000000000002` | ETH -> Bridge -> TRON -> VASP-IND-07 |
| 3 | `0x5c6edemo3suspectwallet0000000000000003` | High-risk 4-wallet cluster -> VASP-IND-11 |

Any other string (for example `0xdeadbeef1234`) produces a synthetic deterministic trace.

## 4. Set up LIVE MODE (optional: real Etherscan / TRONSCAN data)

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

**Getting an Etherscan API key**

1. Sign up at https://etherscan.io/register
2. Create a key at https://etherscan.io/apidashboard
3. That one key works across Etherscan's unified **API V2**, the endpoint this project calls: `https://api.etherscan.io/v2/api?chainid=1&...`. The old per-chain V1 endpoints (`api.etherscan.io/api` with no `chainid`) were deprecated on 15 Aug 2025, and this adapter already targets the current V2 format.

**Getting a TRONSCAN key (optional)**

See https://docs.tronscan.org/. You don't need a key to try LIVE MODE on TRON; having one just raises the rate limit.

After editing `.env`, restart the backend with `uvicorn app.main:app --port 8000`.

In the UI, click the **LIVE** toggle in the top bar, pick a chain, paste a real wallet address, and click **ANALYZE WALLET**. The BLOCKCHAIN API STATUS panel shows whether each key is configured before you run anything.

If a live call fails for any reason (no key, rate limit, timeout, invalid address, or no transactions), you'll see a **LIVE DATA UNAVAILABLE** banner with the reason and a **Switch to Demo Case** button. The app never crashes, and DEMO MODE is always one click away.

## Notes

- All DEMO MODE wallet addresses, transaction hashes, and the VASP registry are **synthetic**, and are clearly labelled "Demo VASP Intelligence Dataset" in the UI and the PDF report. That registry is never claimed to contain real exchange addresses, in DEMO or LIVE MODE, so a real wallet is not expected to match it.
- Risk scoring in both modes is a transparent weighted sum over 7 explainable signals, never a random number. See `engine.py::score_risk` and `dataset.py::RISK_WEIGHTS` for DEMO, and `live_tracing.py::_derive_signals` for LIVE.
- LIVE MODE tracing is bounded (`MAX_HOPS`, `MAX_WALLETS`, and `MAX_TRANSACTIONS_PER_WALLET` in `.env`) and cached (`CACHE_TTL_SECONDS`); see `live_tracing.py` and `cache.py`. It never crawls without limits, and it never crashes the app when an API fails. See the exception hierarchy in `blockchain/base.py` and `main.py::_analyze_live`.
