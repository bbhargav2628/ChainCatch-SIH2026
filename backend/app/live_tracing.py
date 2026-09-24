"""
LIVE MODE tracing engine.

Fetches real transactions via the Etherscan / TRONSCAN adapters, then runs
a bounded multi-hop traversal, a simple "common destination" clustering
heuristic, VASP-registry matching and explainable risk-signal derivation —
the live-data counterpart to the pre-built demo cases in dataset.py /
engine.py. The output shape matches a DEMO_CASES entry so it flows through
the same engine.build_graph_payload / engine.score_risk / engine.match_vasp
functions and renders in the same dashboard UI.

Guardrails (config.py / .env): MAX_HOPS, MAX_WALLETS and
MAX_TRANSACTIONS_PER_WALLET bound the traversal so a real, highly active
wallet can't trigger unbounded crawling or blow through an API quota.
"""
from collections import defaultdict, deque
from datetime import datetime

from . import cache, config
from .blockchain import etherscan, tronscan
from .blockchain.base import (
    BlockchainAPIError,
    InvalidAddressError,
    MissingAPIKeyError,
    NoTransactionsError,
    is_valid_ethereum_address,
    is_valid_tron_address,
)
from .dataset import VASP_REGISTRY

ADAPTERS = {"ethereum": etherscan, "tron": tronscan}


def trace_wallet(wallet: str, chain: str):
    """
    Returns (case, meta) where `case` matches the DEMO_CASES shape and
    `meta` carries {"data_source", "adapter", "fetch_errors", "wallets_visited"}
    for the UI's DATA SOURCE / API status indicators.

    Raises a BlockchainAPIError subclass (never a raw exception) on any
    failure — the caller (main.py) turns that into a clean HTTP error the
    frontend can show and recover from without crashing.
    """
    chain = (chain or "").lower().strip()
    if chain not in ADAPTERS:
        raise BlockchainAPIError(f"Unsupported chain '{chain}'. Choose ethereum or tron.", code="unsupported_chain")

    wallet = wallet.strip()
    validator = is_valid_ethereum_address if chain == "ethereum" else is_valid_tron_address
    if not validator(wallet):
        raise InvalidAddressError(chain.capitalize(), wallet)

    api_key = config.ETHERSCAN_API_KEY if chain == "ethereum" else config.TRONSCAN_API_KEY
    if chain == "ethereum" and not api_key:
        raise MissingAPIKeyError("Etherscan")
    # TRONSCAN works keyless (lower rate limit) so it isn't hard-required here.

    adapter = ADAPTERS[chain]

    nodes, node_ids, edges = [], {}, []
    visited = set()
    total_tx_seen = 0
    data_sources = set()
    fetch_errors = []
    vasp_endpoint_node = None
    hops_traced = 0

    def get_or_create_node(address, hop):
        key = address.lower()
        if key in node_ids:
            return node_ids[key]
        vasp = VASP_REGISTRY.get(key) or VASP_REGISTRY.get(address)
        nid = f"W{len(nodes)}"
        ntype = "vasp" if vasp else ("suspect" if hop == 0 else "wallet")
        node = {
            "id": nid,
            "address": address,
            "chain": chain.capitalize(),
            "type": ntype,
            "label": vasp["vasp_id"] if vasp else ("Suspect Wallet" if hop == 0 else f"Wallet {len(nodes)}"),
        }
        if vasp:
            node["risk"] = "high"
        nodes.append(node)
        node_ids[key] = nid
        return nid

    get_or_create_node(wallet, 0)
    frontier = deque([(wallet, 0)])

    while frontier and len(nodes) < config.MAX_WALLETS:
        address, hop = frontier.popleft()
        if address.lower() in visited or hop > config.MAX_HOPS:
            continue
        visited.add(address.lower())

        cached = cache.get(chain, address, config.CACHE_TTL_SECONDS)
        if cached is not None:
            txs = cached
            data_sources.add("cache")
        else:
            try:
                tx_objs = adapter.fetch_transactions(
                    address, api_key, config.MAX_TRANSACTIONS_PER_WALLET, config.REQUEST_TIMEOUT_SECONDS,
                )
            except BlockchainAPIError:
                if address.lower() == wallet.lower():
                    raise  # a failure on the reported wallet aborts the whole analysis
                fetch_errors.append(address)
                continue
            txs = [t.to_dict() for t in tx_objs]
            cache.set(chain, address, txs)
            data_sources.add("live")

        if address.lower() == wallet.lower() and not txs:
            raise NoTransactionsError(chain.capitalize(), wallet)

        total_tx_seen += len(txs)
        src_id = node_ids[address.lower()]

        # Follow only this wallet's own OUTGOING transfers, so the trace stays
        # anchored on where the reported wallet's funds went (not every
        # counterparty's unrelated history).
        outgoing = sorted(
            (t for t in txs if t["from"].lower() == address.lower() and t["to"]),
            key=lambda t: t["timestamp"],
        )

        for t in outgoing[:config.MAX_TRANSACTIONS_PER_WALLET]:
            if len(nodes) >= config.MAX_WALLETS:
                break
            counterparty = t["to"]
            dst_id = get_or_create_node(counterparty, hop + 1)
            edges.append({
                "id": f"T{len(edges) + 1}", "source": src_id, "target": dst_id,
                "amount": t["amount"], "asset": t["asset"], "timestamp": t["timestamp"],
                "block": t["block_number"], "chain": chain.capitalize(), "tx_hash": t["tx_hash"],
            })
            hops_traced = max(hops_traced, hop + 1)
            is_vasp = bool(VASP_REGISTRY.get(counterparty.lower()) or VASP_REGISTRY.get(counterparty))
            if is_vasp:
                vasp_endpoint_node = dst_id
            elif hop + 1 <= config.MAX_HOPS:
                frontier.append((counterparty, hop + 1))

    edges = _dedupe_edges(edges)
    clusters = _detect_clusters(edges)
    signals = _derive_signals(nodes, edges, hops_traced, vasp_endpoint_node is not None, clusters)

    data_source = "live" if "live" in data_sources else ("cache" if data_sources else "live")

    case = {
        "label": f"Live {chain.capitalize()} trace",
        "reported_wallet": wallet,
        "primary_chain": chain.capitalize(),
        "chains_analyzed": [chain.capitalize()],
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters,
        "vasp_endpoint_node": vasp_endpoint_node,
        "cross_chain": None,
        "signals": signals,
        "total_transactions_analyzed": total_tx_seen,
    }
    meta = {
        "data_source": data_source,
        "adapter": "etherscan" if chain == "ethereum" else "tronscan",
        "fetch_errors": fetch_errors,
        "wallets_visited": len(visited),
    }
    return case, meta


def _dedupe_edges(edges):
    seen, out = set(), []
    for e in edges:
        key = e["tx_hash"] or (e["source"], e["target"], e["timestamp"])
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def _detect_clusters(edges):
    """Wallets that send to the SAME downstream wallet within this trace —
    a simple, explainable 'common destination' clustering heuristic."""
    incoming = defaultdict(list)
    for e in edges:
        incoming[e["target"]].append(e["source"])

    clusters, cid, claimed = [], 1, set()
    for sources in incoming.values():
        distinct = [w for w in dict.fromkeys(sources) if w not in claimed]
        if len(distinct) >= 2:
            clusters.append({
                "cluster_id": f"LC{cid}",
                "wallet_ids": distinct,
                "characteristics": [
                    "multiple wallets converge on the same downstream wallet in the live trace",
                    "connected fund flows observed on-chain",
                ],
                "risk": "medium",
            })
            claimed.update(distinct)
            cid += 1
    return clusters


def _derive_signals(nodes, edges, hops_traced, vasp_hit, clusters):
    wallets = [n for n in nodes if n["type"] in ("suspect", "wallet")]
    senders = {e["source"] for e in edges}

    continuity = (len(senders) / len(wallets)) if wallets else 0.0
    proximity = max(0.0, 1 - (hops_traced / max(config.MAX_HOPS, 1))) if hops_traced else 0.3
    timing = _timing_signal(edges)
    amount_corr = _amount_signal(edges)

    return {
        "fund_flow_continuity": round(min(1.0, continuity), 2),
        "wallet_proximity": round(min(1.0, proximity), 2),
        "transaction_timing": round(timing, 2),
        "amount_correlation": round(amount_corr, 2),
        "vasp_interaction": 1.0 if vasp_hit else 0.0,
        "cluster_behavior": round(min(1.0, 0.3 + 0.25 * len(clusters)), 2) if clusters else 0.1,
        "cross_chain_signals": 0.0,  # this trace is single-chain; see cross-chain notes in README
    }


def _timing_signal(edges):
    if len(edges) < 2:
        return 0.3
    try:
        times = sorted(datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) for e in edges)
    except (ValueError, TypeError):
        return 0.3
    gaps = [(b - a).total_seconds() / 60 for a, b in zip(times, times[1:])]
    avg_gap = (sum(gaps) / len(gaps)) if gaps else 999
    return max(0.0, min(1.0, 1 - avg_gap / 240))


def _amount_signal(edges):
    amounts = [e["amount"] for e in edges if e.get("amount")]
    if len(amounts) < 2:
        return 0.3
    lo, hi = min(amounts), max(amounts)
    if hi == 0:
        return 0.3
    return max(0.0, min(1.0, lo / hi))
