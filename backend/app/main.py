import random
import string
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import config, engine, live_tracing
from .blockchain.base import BlockchainAPIError
from .dataset import DATASET_LABEL
from .report import build_report_pdf

app = FastAPI(title="ChainCatch API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store of generated analyses, keyed by case_id (fine for a local demo)
ANALYSIS_STORE: dict = {}


def _new_case_id() -> str:
    return "NCRP-2026-" + "".join(random.choices(string.digits, k=6))


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "DEMO"}


@app.get("/api/status")
def api_status():
    """Powers the LIVE MODE 'BLOCKCHAIN API STATUS' panel. Never returns key values."""
    return {
        "ethereum": {
            "adapter": "etherscan",
            "configured": bool(config.ETHERSCAN_API_KEY),
        },
        "tron": {
            "adapter": "tronscan",
            "configured": True,  # TRONSCAN works keyless, at a lower rate limit
            "key_configured": bool(config.TRONSCAN_API_KEY),
        },
        "vasp_dataset": {"loaded": True, "label": DATASET_LABEL},
        "limits": {
            "max_hops": config.MAX_HOPS,
            "max_wallets": config.MAX_WALLETS,
            "max_transactions_per_wallet": config.MAX_TRANSACTIONS_PER_WALLET,
            "cache_ttl_seconds": config.CACHE_TTL_SECONDS,
        },
    }


@app.get("/api/demo-cases")
def demo_cases():
    return {"cases": engine.list_demo_cases()}


@app.get("/api/analyze")
def analyze(
    wallet: str = Query(..., min_length=3),
    mode: str = Query("demo", pattern="^(demo|live)$"),
    chain: str = Query(None, description="Required when mode=live: 'ethereum' or 'tron'"),
):
    wallet = wallet.strip()

    if mode == "live":
        return _analyze_live(wallet, chain)
    return _analyze_demo(wallet)


def _analyze_demo(wallet: str):
    case_key, case = engine.find_case_by_wallet(wallet)
    result_mode = "demo"
    if case is None:
        case = engine.generate_synthetic_case(wallet)
        result_mode = "synthetic"

    nodes, edges, hops_traced = engine.build_graph_payload(case)
    data_source = "demo_dataset" if result_mode == "demo" else "synthetic_offline"
    return _finalize(case, nodes, edges, hops_traced, result_mode, data_source)


def _analyze_live(wallet: str, chain: str):
    if not chain:
        raise HTTPException(
            status_code=400,
            detail={"reason": "Select a blockchain (ethereum or tron) for LIVE MODE.", "code": "missing_chain"},
        )
    try:
        case, meta = live_tracing.trace_wallet(wallet, chain)
    except BlockchainAPIError as e:
        # Never crash the app on a live-API failure: return a clear, structured
        # error so the frontend can show "LIVE DATA UNAVAILABLE" + fall back to DEMO MODE.
        client_error_codes = {"invalid_address", "missing_api_key", "unsupported_chain", "no_transactions"}
        status_code = 400 if e.code in client_error_codes else 502
        raise HTTPException(status_code=status_code, detail={"reason": e.reason, "code": e.code})

    nodes, edges, hops_traced = engine.build_graph_payload(case, use_real_hash=True)
    return _finalize(
        case, nodes, edges, hops_traced, "live",
        data_source=meta["data_source"], adapter=meta["adapter"],
    )


def _finalize(case, nodes, edges, hops_traced, mode, data_source, adapter=None):
    id_to_label = {n["id"]: n["label"] for n in nodes}
    for e in edges:
        e["source_label"] = id_to_label.get(e["source"], e["source"])
        e["target_label"] = id_to_label.get(e["target"], e["target"])

    risk = engine.score_risk(case["signals"])
    vasp_match = engine.match_vasp(case)

    relevant_tx = len(edges)
    primary_asset = edges[0]["asset"] if edges else ""
    total_amt = sum(e["amount"] for e in edges if e["asset"] == primary_asset)

    case_id = _new_case_id()
    analysis = {
        "case_id": case_id,
        "mode": mode,  # "demo" | "synthetic" | "live"
        "data_source": data_source,  # "demo_dataset" | "synthetic_offline" | "live" | "cache"
        "adapter": adapter,  # "etherscan" | "tronscan" | None
        "dataset_label": DATASET_LABEL,
        "reported_wallet": case["reported_wallet"],
        "primary_chain": case["primary_chain"],
        "chains_analyzed": case["chains_analyzed"],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "summary": {
            "total_transactions_analyzed": case["total_transactions_analyzed"],
            "relevant_transactions": relevant_tx,
            "hops_traced": hops_traced,
            "total_funds_traced": f"{round(total_amt, 3)} {primary_asset}" if primary_asset else "0",
        },
        "graph": {"nodes": nodes, "edges": edges},
        "clusters": case.get("clusters", []),
        "vasp_match": vasp_match,
        "cross_chain": case.get("cross_chain"),
        "risk": risk,
    }

    ANALYSIS_STORE[case_id] = analysis
    return analysis


@app.get("/api/report/{case_id}")
def get_report(case_id: str):
    analysis = ANALYSIS_STORE.get(case_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Case not found. Run /api/analyze first.")
    pdf_bytes = build_report_pdf(analysis)
    headers = {"Content-Disposition": f'attachment; filename="ChainCatch_{case_id}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
