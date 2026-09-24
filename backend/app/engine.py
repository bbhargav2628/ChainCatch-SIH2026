"""
ChainCatch analysis engine.

Everything here is intentionally simple and deterministic:
- No live blockchain calls (DEMO MODE only, see live.py for the optional
  LIVE MODE hook).
- Risk scoring is a transparent weighted sum over explainable 0..1 signals,
  never a random number.
- Layout is a plain layered (BFS-depth) layout so the frontend can just
  draw the coordinates it's given.
"""

import hashlib
import random
from datetime import datetime, timedelta

import networkx as nx

from .dataset import (
    DEMO_CASES,
    VASP_REGISTRY,
    RISK_WEIGHTS,
    SIGNAL_LABELS,
    SIGNAL_REASON_TEXT,
    DATASET_LABEL,
)

RISK_HIGH = 80
RISK_MEDIUM = 50


# ---------------------------------------------------------------------------
# Risk scoring — transparent, rule-based, explainable
# ---------------------------------------------------------------------------
def score_risk(signals: dict) -> dict:
    breakdown = []
    total = 0.0
    for key, weight in RISK_WEIGHTS.items():
        value = max(0.0, min(1.0, signals.get(key, 0.0)))
        contribution = value * weight * 100
        total += contribution
        breakdown.append({
            "signal": SIGNAL_LABELS[key],
            "key": key,
            "weight_pct": round(weight * 100),
            "value": round(value, 2),
            "contribution": round(contribution, 1),
        })

    score = round(total)
    level = "HIGH" if score >= RISK_HIGH else ("MEDIUM" if score >= RISK_MEDIUM else "LOW")

    # Reasons: only surface signals that meaningfully contributed
    reasons = [
        SIGNAL_REASON_TEXT[b["key"]] for b in breakdown if b["value"] >= 0.6
    ]
    if not reasons:
        reasons = ["No strong explainable signals were found for this wallet in the demo dataset."]

    # Confidence is a function of how many independent signal families fired strongly
    strong_signals = sum(1 for b in breakdown if b["value"] >= 0.6)
    confidence = min(97, 55 + strong_signals * 7)

    return {
        "score": score,
        "level": level,
        "confidence": confidence,
        "breakdown": breakdown,
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# Layered layout (BFS depth from the reported wallet)
# ---------------------------------------------------------------------------
def compute_layout(nodes: list, edges: list, root_id: str):
    g = nx.DiGraph()
    for n in nodes:
        g.add_node(n["id"])
    for e in edges:
        g.add_edge(e["source"], e["target"])

    depths = {root_id: 0}
    frontier = [root_id]
    seen = {root_id}
    while frontier:
        nxt = []
        for node in frontier:
            for neigh in g.successors(node):
                if neigh not in seen:
                    seen.add(neigh)
                    depths[neigh] = depths[node] + 1
                    nxt.append(neigh)
        frontier = nxt
    # any disconnected node (shouldn't normally happen) gets depth 0
    for n in nodes:
        depths.setdefault(n["id"], 0)

    by_depth = {}
    for n in nodes:
        by_depth.setdefault(depths[n["id"]], []).append(n["id"])

    x_gap, y_gap = 220, 130
    positions = {}
    max_depth = max(by_depth.keys()) if by_depth else 0
    for depth, ids in by_depth.items():
        count = len(ids)
        for i, node_id in enumerate(ids):
            y = (i - (count - 1) / 2) * y_gap
            positions[node_id] = {"x": depth * x_gap + 80, "y": y + 260}

    hops_traced = max_depth
    return positions, hops_traced


def build_graph_payload(case: dict, use_real_hash: bool = False):
    """
    use_real_hash=False (DEMO/synthetic): edges carry no real chain data, so a
    deterministic fake hash is generated for display.
    use_real_hash=True (LIVE): edges already carry a real tx_hash from the
    blockchain adapter — keep it as-is instead of overwriting it.
    """
    nodes = case["nodes"]
    edges = case["edges"]
    root_id = nodes[0]["id"]
    positions, hops_traced = compute_layout(nodes, edges, root_id)

    cluster_map = {}
    for c in case.get("clusters", []):
        for wid in c["wallet_ids"]:
            cluster_map[wid] = c["cluster_id"]

    out_nodes = []
    for n in nodes:
        pos = positions[n["id"]]
        out_nodes.append({
            **n,
            "x": pos["x"],
            "y": pos["y"],
            "cluster": cluster_map.get(n["id"], n.get("cluster")),
        })

    if use_real_hash:
        out_edges = [dict(e) for e in edges]
    else:
        out_edges = [dict(e, tx_hash=_fake_hash(e["id"] + e["source"] + e["target"])) for e in edges]

    return out_nodes, out_edges, hops_traced


def _fake_hash(seed: str) -> str:
    h = hashlib.sha256(seed.encode()).hexdigest()
    return "0xdemo" + h[:58]


# ---------------------------------------------------------------------------
# VASP matching
# ---------------------------------------------------------------------------
def match_vasp(case: dict):
    node_id = case.get("vasp_endpoint_node")
    if not node_id:
        return None
    node = next(n for n in case["nodes"] if n["id"] == node_id)
    reg = VASP_REGISTRY.get(node["address"])
    if not reg:
        return None
    return {
        **reg,
        "address": node["address"],
        "confidence": 91,
        "evidence": [
            "traced endpoint matches a labelled wallet in the demo VASP registry",
            "repeated interaction across the traced path",
            "high fund concentration at this endpoint relative to upstream hops",
            "temporal and path evidence consistent with a fund-flow destination",
        ],
        "dataset_label": DATASET_LABEL,
    }


# ---------------------------------------------------------------------------
# Demo-case lookup
# ---------------------------------------------------------------------------
def find_case_by_wallet(wallet: str):
    wallet_norm = wallet.strip().lower()
    for case_id, case in DEMO_CASES.items():
        if case["reported_wallet"].lower() == wallet_norm:
            return case_id, case
    return None, None


def list_demo_cases():
    return [
        {"case_key": key, "label": c["label"], "reported_wallet": c["reported_wallet"], "primary_chain": c["primary_chain"]}
        for key, c in DEMO_CASES.items()
    ]


# ---------------------------------------------------------------------------
# Deterministic synthetic fallback — for ANY address the investigator types
# that isn't one of the 3 curated demo cases. Seeded on the address so the
# same input always reproduces the same trace (fully offline, no network).
# ---------------------------------------------------------------------------
def generate_synthetic_case(wallet: str):
    seed = int(hashlib.sha256(wallet.encode()).hexdigest(), 16) % (2 ** 32)
    rng = random.Random(seed)

    chain = rng.choice(["Ethereum", "TRON"])
    asset = "ETH" if chain == "Ethereum" else "USDT"
    n_hops = rng.randint(2, 3)
    branch = rng.random() > 0.5

    nodes = [{"id": "W0", "address": wallet, "label": "Suspect Wallet", "type": "suspect", "chain": chain}]
    edges = []
    base_amount = round(rng.uniform(1.5, 9.5), 2)
    base_time = datetime(2026, rng.randint(1, 8), rng.randint(1, 27), rng.randint(0, 23), rng.randint(0, 59))

    prev_ids = ["W0"]
    node_counter = 1
    for hop in range(1, n_hops + 1):
        this_ids = []
        fanout = 2 if (branch and hop == 1) else 1
        for b in range(fanout):
            nid = f"W{node_counter}"
            node_counter += 1
            label = chr(ord("A") + node_counter - 2)
            nodes.append({
                "id": nid,
                "address": _synthetic_address(rng, chain),
                "label": f"Wallet {label}",
                "type": "wallet",
                "chain": chain,
            })
            for pid in prev_ids:
                amt = round(base_amount * rng.uniform(0.85, 1.0), 3)
                base_time += timedelta(minutes=rng.randint(5, 90))
                edges.append({
                    "id": f"T{len(edges)+1}",
                    "source": pid,
                    "target": nid,
                    "amount": amt,
                    "asset": asset,
                    "timestamp": base_time.isoformat() + "Z",
                    "block": 19000000 + rng.randint(1000, 900000),
                    "chain": chain,
                })
            this_ids.append(nid)
        prev_ids = this_ids

    # converge to an endpoint, then to a VASP from the registry (same chain if possible)
    endpoint_id = f"W{node_counter}"
    node_counter += 1
    nodes.append({
        "id": endpoint_id, "address": _synthetic_address(rng, chain),
        "label": f"Wallet {chr(ord('A') + node_counter - 2)}", "type": "wallet", "chain": chain, "risk": "high",
    })
    for pid in prev_ids:
        amt = round(base_amount * rng.uniform(0.9, 1.0), 3)
        base_time += timedelta(minutes=rng.randint(5, 40))
        edges.append({
            "id": f"T{len(edges)+1}", "source": pid, "target": endpoint_id,
            "amount": amt, "asset": asset, "timestamp": base_time.isoformat() + "Z",
            "block": 19000000 + rng.randint(1000, 900000), "chain": chain,
        })
    prev_ids = [endpoint_id]

    vasp_candidates = [addr for addr, v in VASP_REGISTRY.items() if v["chain"] == chain]
    vasp_addr = rng.choice(vasp_candidates) if vasp_candidates else rng.choice(list(VASP_REGISTRY.keys()))
    vasp_id = "V0"
    nodes.append({
        "id": vasp_id, "address": vasp_addr,
        "label": VASP_REGISTRY[vasp_addr]["vasp_id"], "type": "vasp", "chain": VASP_REGISTRY[vasp_addr]["chain"],
        "risk": "high",
    })
    base_time += timedelta(minutes=rng.randint(10, 60))
    edges.append({
        "id": f"T{len(edges)+1}", "source": endpoint_id, "target": vasp_id,
        "amount": round(base_amount * fanout if branch else base_amount, 3), "asset": asset,
        "timestamp": base_time.isoformat() + "Z", "block": 19000000 + rng.randint(1000, 900000), "chain": chain,
    })

    cluster = None
    if branch:
        cluster_wallets = [n["id"] for n in nodes if n["type"] == "wallet"][:3]
        cluster = {
            "cluster_id": "SC1",
            "wallet_ids": cluster_wallets,
            "characteristics": ["connected fund flows", "similar timing", "common downstream destination"],
            "risk": "medium",
        }

    signals = {
        "fund_flow_continuity": round(rng.uniform(0.55, 0.9), 2),
        "wallet_proximity": round(rng.uniform(0.5, 0.9), 2),
        "transaction_timing": round(rng.uniform(0.4, 0.85), 2),
        "amount_correlation": round(rng.uniform(0.5, 0.9), 2),
        "vasp_interaction": round(rng.uniform(0.6, 0.95), 2),
        "cluster_behavior": round(rng.uniform(0.3, 0.85), 2) if branch else round(rng.uniform(0.1, 0.4), 2),
        "cross_chain_signals": 0.0,
    }

    case = {
        "label": "Synthetic demo trace (generated offline for this address)",
        "reported_wallet": wallet,
        "primary_chain": chain,
        "chains_analyzed": [chain],
        "nodes": nodes,
        "edges": edges,
        "clusters": [cluster] if cluster else [],
        "vasp_endpoint_node": vasp_id,
        "cross_chain": None,
        "signals": signals,
        "total_transactions_analyzed": rng.randint(60, 260),
    }
    return case


def _synthetic_address(rng: random.Random, chain: str) -> str:
    hexchars = "0123456789abcdef"
    body = "".join(rng.choice(hexchars) for _ in range(38))
    return ("0xdemo" + body) if chain == "Ethereum" else ("Tdemo" + body[:34])
