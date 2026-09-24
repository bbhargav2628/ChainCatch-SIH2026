"""
ChainCatch — Demo / Pre-indexed Dataset
=========================================
Everything in this file is SYNTHETIC data built for the SIH 2026 prototype
demo. Addresses, tx hashes and the VASP registry are fabricated for
demonstration purposes only and must never be presented as real blockchain
records or real Indian exchanges.
"""

DATASET_LABEL = "Demo VASP Intelligence Dataset (synthetic, for prototype demonstration only)"

# ---------------------------------------------------------------------------
# Labelled VASP / exchange endpoint registry (synthetic)
# ---------------------------------------------------------------------------
VASP_REGISTRY = {
    "0xvaspind04demoendpoint000000000000000001": {
        "vasp_id": "VASP-IND-04",
        "name": "Demo Exchange — VASP-IND-04",
        "chain": "Ethereum",
        "classification": "Likely Exchange Endpoint",
    },
    "TVaspInd07DemoEndpoint00000000000000002": {
        "vasp_id": "VASP-IND-07",
        "name": "Demo Exchange — VASP-IND-07",
        "chain": "TRON",
        "classification": "Likely Exchange Endpoint",
    },
    "0xvaspind11demoendpoint000000000000000003": {
        "vasp_id": "VASP-IND-11",
        "name": "Demo Exchange — VASP-IND-11",
        "chain": "Ethereum",
        "classification": "Likely Exchange Endpoint",
    },
}

# ---------------------------------------------------------------------------
# Pre-built demo cases
# ---------------------------------------------------------------------------
# Each case is a small, hand-authored fund-flow graph. "signals" are the raw
# 0..1 explainable-risk inputs that the risk engine turns into a score —
# they are NOT a random final number, see engine.py::score_risk().

DEMO_CASES = {
    "CASE-1-MULTIHOP": {
        "label": "Case 1 · Ethereum multi-hop → VASP",
        "reported_wallet": "0x7a3fdemo1suspectwallet0000000000000001",
        "primary_chain": "Ethereum",
        "chains_analyzed": ["Ethereum"],
        "nodes": [
            {"id": "W0", "address": "0x7a3fdemo1suspectwallet0000000000000001", "label": "Suspect Wallet", "type": "suspect", "chain": "Ethereum"},
            {"id": "W1", "address": "0x1b2ademo1hop10000000000000000000000011", "label": "Wallet A", "type": "wallet", "chain": "Ethereum"},
            {"id": "W2", "address": "0x2c3bdemo1hop20000000000000000000000012", "label": "Wallet B", "type": "wallet", "chain": "Ethereum", "cluster": "C1"},
            {"id": "W3", "address": "0x3d4cdemo1hop20000000000000000000000013", "label": "Wallet C", "type": "wallet", "chain": "Ethereum", "cluster": "C1"},
            {"id": "W4", "address": "0x4e5ddemo1hop30000000000000000000000014", "label": "Wallet D", "type": "wallet", "chain": "Ethereum", "cluster": "C1", "risk": "high"},
            {"id": "V0", "address": "0xvaspind04demoendpoint000000000000000001", "label": "VASP-IND-04", "type": "vasp", "chain": "Ethereum", "risk": "high"},
        ],
        "edges": [
            {"id": "T1", "source": "W0", "target": "W1", "amount": 8.4, "asset": "ETH", "timestamp": "2026-01-14T09:12:03Z", "block": 19042113, "chain": "Ethereum"},
            {"id": "T2", "source": "W1", "target": "W2", "amount": 4.1, "asset": "ETH", "timestamp": "2026-01-14T09:47:51Z", "block": 19042201, "chain": "Ethereum"},
            {"id": "T3", "source": "W1", "target": "W3", "amount": 4.2, "asset": "ETH", "timestamp": "2026-01-14T09:49:12Z", "block": 19042203, "chain": "Ethereum"},
            {"id": "T4", "source": "W2", "target": "W4", "amount": 4.0, "asset": "ETH", "timestamp": "2026-01-14T10:22:40Z", "block": 19042340, "chain": "Ethereum"},
            {"id": "T5", "source": "W3", "target": "W4", "amount": 4.1, "asset": "ETH", "timestamp": "2026-01-14T10:23:58Z", "block": 19042342, "chain": "Ethereum"},
            {"id": "T6", "source": "W4", "target": "V0", "amount": 8.0, "asset": "ETH", "timestamp": "2026-01-14T11:05:22Z", "block": 19042510, "chain": "Ethereum"},
        ],
        "clusters": [
            {
                "cluster_id": "C1",
                "wallet_ids": ["W2", "W3", "W4"],
                "characteristics": ["connected fund flows", "similar timing", "common destination (VASP-IND-04)"],
                "risk": "high",
            }
        ],
        "vasp_endpoint_node": "V0",
        "cross_chain": None,
        "signals": {
            "fund_flow_continuity": 0.95,
            "wallet_proximity": 0.9,
            "transaction_timing": 0.85,
            "amount_correlation": 0.9,
            "vasp_interaction": 1.0,
            "cluster_behavior": 0.9,
            "cross_chain_signals": 0.0,
        },
        "total_transactions_analyzed": 214,
    },

    "CASE-2-CROSSCHAIN": {
        "label": "Case 2 · Ethereum → Bridge → TRON → VASP",
        "reported_wallet": "0x9f1edemo2suspectwallet0000000000000002",
        "primary_chain": "Ethereum",
        "chains_analyzed": ["Ethereum", "TRON"],
        "nodes": [
            {"id": "W0", "address": "0x9f1edemo2suspectwallet0000000000000002", "label": "Suspect Wallet", "type": "suspect", "chain": "Ethereum"},
            {"id": "W1", "address": "0x8a2fdemo2hop10000000000000000000000021", "label": "Wallet A", "type": "wallet", "chain": "Ethereum"},
            {"id": "B0", "address": "bridge-contract-demo-0000000000000022", "label": "Cross-Chain Bridge", "type": "bridge", "chain": "Ethereum→TRON"},
            {"id": "W2", "address": "TWalletBdemo2hop2000000000000000000023", "label": "Wallet B", "type": "wallet", "chain": "TRON"},
            {"id": "W3", "address": "TWalletCdemo2hop3000000000000000000024", "label": "Wallet C", "type": "wallet", "chain": "TRON", "cluster": "C2"},
            {"id": "V0", "address": "TVaspInd07DemoEndpoint00000000000000002", "label": "VASP-IND-07", "type": "vasp", "chain": "TRON", "risk": "high"},
        ],
        "edges": [
            {"id": "T1", "source": "W0", "target": "W1", "amount": 6.2, "asset": "ETH", "timestamp": "2026-02-02T03:11:09Z", "block": 19301120, "chain": "Ethereum"},
            {"id": "T2", "source": "W1", "target": "B0", "amount": 6.0, "asset": "ETH", "timestamp": "2026-02-02T03:40:27Z", "block": 19301188, "chain": "Ethereum"},
            {"id": "T3", "source": "B0", "target": "W2", "amount": 18500, "asset": "USDT", "timestamp": "2026-02-02T03:52:14Z", "block": 61820044, "chain": "TRON"},
            {"id": "T4", "source": "W2", "target": "W3", "amount": 18000, "asset": "USDT", "timestamp": "2026-02-02T04:15:39Z", "block": 61820210, "chain": "TRON"},
            {"id": "T5", "source": "W3", "target": "V0", "amount": 17950, "asset": "USDT", "timestamp": "2026-02-02T04:48:02Z", "block": 61820390, "chain": "TRON"},
        ],
        "clusters": [
            {
                "cluster_id": "C2",
                "wallet_ids": ["W2", "W3"],
                "characteristics": ["post-bridge fund concentration", "rapid sequential transfer", "common destination (VASP-IND-07)"],
                "risk": "high",
            }
        ],
        "vasp_endpoint_node": "V0",
        "cross_chain": {
            "from_chain": "Ethereum",
            "to_chain": "TRON",
            "bridge_node": "B0",
            "evidence": [
                "value correlation: 6.0 ETH bridged ≈ 18,500 USDT at prevailing demo rate",
                "timing correlation: TRON-side deposit occurs 12 min after Ethereum-side bridge transfer",
                "asset correlation: bridge deposit/withdrawal pair matched on the bridge contract's demo event log",
            ],
        },
        "signals": {
            "fund_flow_continuity": 0.88,
            "wallet_proximity": 0.8,
            "transaction_timing": 0.9,
            "amount_correlation": 0.85,
            "vasp_interaction": 0.95,
            "cluster_behavior": 0.75,
            "cross_chain_signals": 1.0,
        },
        "total_transactions_analyzed": 341,
    },

    "CASE-3-CLUSTER": {
        "label": "Case 3 · High-risk wallet cluster",
        "reported_wallet": "0x5c6edemo3suspectwallet0000000000000003",
        "primary_chain": "Ethereum",
        "chains_analyzed": ["Ethereum"],
        "nodes": [
            {"id": "W0", "address": "0x5c6edemo3suspectwallet0000000000000003", "label": "Suspect Wallet", "type": "suspect", "chain": "Ethereum"},
            {"id": "W1", "address": "0x1111demo3branch10000000000000000000031", "label": "Wallet A", "type": "wallet", "chain": "Ethereum", "cluster": "C3"},
            {"id": "W2", "address": "0x2222demo3branch20000000000000000000032", "label": "Wallet B", "type": "wallet", "chain": "Ethereum", "cluster": "C3"},
            {"id": "W3", "address": "0x3333demo3branch30000000000000000000033", "label": "Wallet C", "type": "wallet", "chain": "Ethereum", "cluster": "C3"},
            {"id": "W4", "address": "0x4444demo3branch40000000000000000000034", "label": "Wallet D", "type": "wallet", "chain": "Ethereum", "cluster": "C3", "risk": "high"},
            {"id": "V0", "address": "0xvaspind11demoendpoint000000000000000003", "label": "VASP-IND-11", "type": "vasp", "chain": "Ethereum", "risk": "high"},
        ],
        "edges": [
            {"id": "T1", "source": "W0", "target": "W1", "amount": 2.1, "asset": "ETH", "timestamp": "2026-03-05T14:02:11Z", "block": 19582011, "chain": "Ethereum"},
            {"id": "T2", "source": "W0", "target": "W2", "amount": 2.0, "asset": "ETH", "timestamp": "2026-03-05T14:03:47Z", "block": 19582014, "chain": "Ethereum"},
            {"id": "T3", "source": "W0", "target": "W3", "amount": 2.2, "asset": "ETH", "timestamp": "2026-03-05T14:04:52Z", "block": 19582016, "chain": "Ethereum"},
            {"id": "T4", "source": "W1", "target": "W4", "amount": 2.0, "asset": "ETH", "timestamp": "2026-03-05T15:10:33Z", "block": 19582290, "chain": "Ethereum"},
            {"id": "T5", "source": "W2", "target": "W4", "amount": 1.95, "asset": "ETH", "timestamp": "2026-03-05T15:11:02Z", "block": 19582291, "chain": "Ethereum"},
            {"id": "T6", "source": "W3", "target": "W4", "amount": 2.1, "asset": "ETH", "timestamp": "2026-03-05T15:12:19Z", "block": 19582293, "chain": "Ethereum"},
            {"id": "T7", "source": "W4", "target": "V0", "amount": 6.0, "asset": "ETH", "timestamp": "2026-03-05T16:00:00Z", "block": 19582510, "chain": "Ethereum"},
        ],
        "clusters": [
            {
                "cluster_id": "C3",
                "wallet_ids": ["W1", "W2", "W3", "W4"],
                "characteristics": [
                    "fan-out from a single reported wallet within 3 minutes",
                    "near-identical transfer amounts (structuring pattern)",
                    "all four wallets reconverge on the same downstream wallet",
                    "common destination (VASP-IND-11)",
                ],
                "risk": "high",
            }
        ],
        "vasp_endpoint_node": "V0",
        "cross_chain": None,
        "signals": {
            "fund_flow_continuity": 0.9,
            "wallet_proximity": 0.95,
            "transaction_timing": 0.95,
            "amount_correlation": 0.8,
            "vasp_interaction": 0.9,
            "cluster_behavior": 1.0,
            "cross_chain_signals": 0.0,
        },
        "total_transactions_analyzed": 178,
    },
}

RISK_WEIGHTS = {
    "fund_flow_continuity": 0.20,
    "wallet_proximity": 0.20,
    "transaction_timing": 0.15,
    "amount_correlation": 0.15,
    "vasp_interaction": 0.15,
    "cluster_behavior": 0.10,
    "cross_chain_signals": 0.05,
}

SIGNAL_LABELS = {
    "fund_flow_continuity": "Fund-flow continuity",
    "wallet_proximity": "Wallet proximity",
    "transaction_timing": "Transaction timing",
    "amount_correlation": "Amount correlation",
    "vasp_interaction": "VASP interaction",
    "cluster_behavior": "Cluster behavior",
    "cross_chain_signals": "Cross-chain signals",
}

SIGNAL_REASON_TEXT = {
    "fund_flow_continuity": "Strong multi-hop fund continuity from the reported wallet",
    "wallet_proximity": "Short graph distance between the reported wallet and the likely endpoint",
    "transaction_timing": "Close temporal relationship between hops (rapid sequential transfers)",
    "amount_correlation": "High-value transfer correlation across hops",
    "vasp_interaction": "Repeated interaction with a labelled VASP wallet",
    "cluster_behavior": "Suspicious wallet cluster detected",
    "cross_chain_signals": "Cross-chain activity detected via bridge correlation",
}
