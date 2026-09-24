"""
Etherscan API adapter — LIVE MODE, Ethereum.

Uses the current Etherscan API V2 unified endpoint (the old per-chain V1
endpoints, e.g. api.etherscan.io/api with no chainid, were deprecated
15 Aug 2025 and now return an explicit "deprecated" error).

Docs: https://docs.etherscan.io/etherscan-v2/api-endpoints
V2 base: https://api.etherscan.io/v2/api?chainid=<id>&...

The API key is read from the backend's own settings (see config.py) and is
never sent to or exposed in the React frontend.
"""
from datetime import datetime, timezone

import httpx

from .base import (
    NormalizedTx,
    MissingAPIKeyError,
    RateLimitError,
    UpstreamTimeoutError,
    UpstreamAPIError,
)

BASE_URL = "https://api.etherscan.io/v2/api"
CHAIN_ID = 1  # Ethereum mainnet under the unified V2 API
CHAIN_NAME = "ethereum"


def fetch_transactions(address: str, api_key: str, max_tx: int, timeout: int):
    """Returns a list[NormalizedTx] for `address`: normal ETH txs + ERC-20 transfers."""
    if not api_key:
        raise MissingAPIKeyError("Etherscan")

    address = address.strip()
    txs = _fetch_normal(address, api_key, max_tx, timeout)

    # ERC-20 transfers are a bonus signal — never let a failure here take
    # down a fetch that already has valid native-ETH transactions.
    try:
        txs += _fetch_token_transfers(address, api_key, max_tx, timeout)
    except MissingAPIKeyError:
        raise
    except Exception:
        pass

    txs.sort(key=lambda t: t.timestamp)
    return txs[-max_tx:] if max_tx else txs


def _get(params: dict, api_key: str, timeout: int) -> dict:
    query = {**params, "chainid": CHAIN_ID, "apikey": api_key}
    try:
        resp = httpx.get(BASE_URL, params=query, timeout=timeout)
    except httpx.TimeoutException:
        raise UpstreamTimeoutError("Etherscan")
    except httpx.HTTPError as e:
        raise UpstreamAPIError("Etherscan", str(e))

    if resp.status_code == 429:
        raise RateLimitError("Etherscan")
    if resp.status_code != 200:
        raise UpstreamAPIError("Etherscan", f"HTTP {resp.status_code}")

    data = resp.json()
    if data.get("status") == "0":
        message = str(data.get("message", "")).lower()
        result = data.get("result")
        if "rate limit" in message or "max calls" in message or "max rate" in message:
            raise RateLimitError("Etherscan")
        if "no transactions found" in message:
            return {"status": "0", "result": []}
        if isinstance(result, str) and "deprecated" in result.lower():
            raise UpstreamAPIError(
                "Etherscan",
                "Received a deprecated-API response — this adapter targets the "
                "current V2 endpoint, check for an Etherscan API change.",
            )
        raise UpstreamAPIError("Etherscan", str(result or data.get("message") or "unknown error"))
    return data


def _fetch_normal(address, api_key, max_tx, timeout):
    data = _get({
        "module": "account", "action": "txlist", "address": address,
        "startblock": 0, "endblock": 99999999, "page": 1,
        "offset": max_tx, "sort": "desc",
    }, api_key, timeout)

    out = []
    for tx in data.get("result", []) or []:
        try:
            value = int(tx.get("value", "0")) / 1e18
        except (TypeError, ValueError):
            value = 0.0
        if value <= 0:
            continue
        out.append(NormalizedTx(
            chain=CHAIN_NAME,
            tx_hash=tx.get("hash", ""),
            from_addr=(tx.get("from") or "").lower(),
            to_addr=(tx.get("to") or "").lower(),
            amount=round(value, 6),
            asset="ETH",
            timestamp=_ts(tx.get("timeStamp")),
            block_number=_int(tx.get("blockNumber")),
            token_address=None,
        ))
    return out


def _fetch_token_transfers(address, api_key, max_tx, timeout):
    data = _get({
        "module": "account", "action": "tokentx", "address": address,
        "page": 1, "offset": max_tx, "sort": "desc",
    }, api_key, timeout)

    out = []
    for tx in data.get("result", []) or []:
        try:
            decimals = int(tx.get("tokenDecimal", "18") or "18")
            value = int(tx.get("value", "0")) / (10 ** decimals)
        except (TypeError, ValueError):
            value = 0.0
        if value <= 0:
            continue
        out.append(NormalizedTx(
            chain=CHAIN_NAME,
            tx_hash=tx.get("hash", ""),
            from_addr=(tx.get("from") or "").lower(),
            to_addr=(tx.get("to") or "").lower(),
            amount=round(value, 6),
            asset=tx.get("tokenSymbol") or "TOKEN",
            timestamp=_ts(tx.get("timeStamp")),
            block_number=_int(tx.get("blockNumber")),
            token_address=(tx.get("contractAddress") or "").lower(),
        ))
    return out


def _ts(unix_seconds) -> str:
    try:
        return datetime.fromtimestamp(int(unix_seconds), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OSError, OverflowError):
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
