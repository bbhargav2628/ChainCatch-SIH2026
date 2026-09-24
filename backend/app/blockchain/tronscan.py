"""
TRONSCAN API adapter — LIVE MODE, TRON.

Docs: https://docs.tronscan.org/en/api/transactions-and-transfers
Base: https://apilist.tronscanapi.com/api

TRONSCAN's public endpoints work without a key at a low rate limit; if
TRONSCAN_API_KEY is set we send it as the TRON-PRO-API-KEY header for a
higher limit. Either way the key never reaches the frontend.
"""
from datetime import datetime, timezone

import httpx

from .base import NormalizedTx, RateLimitError, UpstreamTimeoutError, UpstreamAPIError

BASE_URL = "https://apilist.tronscanapi.com/api"
CHAIN_NAME = "tron"


def fetch_transactions(address: str, api_key, max_tx: int, timeout: int):
    """Returns a list[NormalizedTx] for `address`: TRX txs + TRC-20 transfers."""
    address = address.strip()
    txs = _fetch_trx(address, api_key, max_tx, timeout)

    try:
        txs += _fetch_trc20(address, api_key, max_tx, timeout)
    except Exception:
        pass  # TRC-20 transfers are a bonus signal, never fail the whole fetch

    txs.sort(key=lambda t: t.timestamp)
    return txs[-max_tx:] if max_tx else txs


def _get(path: str, params: dict, api_key, timeout: int) -> dict:
    headers = {"TRON-PRO-API-KEY": api_key} if api_key else {}
    try:
        resp = httpx.get(f"{BASE_URL}{path}", params=params, headers=headers, timeout=timeout)
    except httpx.TimeoutException:
        raise UpstreamTimeoutError("TRONSCAN")
    except httpx.HTTPError as e:
        raise UpstreamAPIError("TRONSCAN", str(e))

    if resp.status_code == 429:
        raise RateLimitError("TRONSCAN")
    if resp.status_code != 200:
        raise UpstreamAPIError("TRONSCAN", f"HTTP {resp.status_code}")
    try:
        return resp.json()
    except ValueError:
        raise UpstreamAPIError("TRONSCAN", "Received a non-JSON response")


def _fetch_trx(address, api_key, max_tx, timeout):
    data = _get("/transaction", {
        "address": address, "limit": min(max_tx, 50) if max_tx else 50,
        "start": 0, "sort": "-timestamp",
    }, api_key, timeout)

    out = []
    for tx in data.get("data", []) or []:
        amount = _sun_to_trx(tx.get("amount"))
        if amount is None or amount <= 0:
            continue
        to_addr = tx.get("toAddress") or tx.get("to_address") or ""
        from_addr = tx.get("ownerAddress") or tx.get("from_address") or ""
        if not to_addr or not from_addr:
            continue
        out.append(NormalizedTx(
            chain=CHAIN_NAME,
            tx_hash=tx.get("hash", ""),
            from_addr=from_addr,
            to_addr=to_addr,
            amount=amount,
            asset="TRX",
            timestamp=_ts_ms(tx.get("timestamp")),
            block_number=_int(tx.get("block")),
        ))
    return out


def _fetch_trc20(address, api_key, max_tx, timeout):
    data = _get("/token_trc20/transfers", {
        "relatedAddress": address, "limit": min(max_tx, 50) if max_tx else 50, "start": 0,
    }, api_key, timeout)

    out = []
    for tx in data.get("token_transfers", []) or []:
        token_info = tx.get("tokenInfo", {}) or {}
        try:
            decimals = int(token_info.get("tokenDecimal", 6) or 6)
            value = int(tx.get("quant", "0")) / (10 ** decimals)
        except (TypeError, ValueError):
            value = 0.0
        if value <= 0:
            continue
        out.append(NormalizedTx(
            chain=CHAIN_NAME,
            tx_hash=tx.get("transaction_id", ""),
            from_addr=tx.get("from_address", ""),
            to_addr=tx.get("to_address", ""),
            amount=round(value, 6),
            asset=token_info.get("tokenAbbr") or "TRC20",
            timestamp=_ts_ms(tx.get("block_ts")),
            block_number=None,
            token_address=token_info.get("tokenId"),
        ))
    return out


def _sun_to_trx(amt):
    if amt is None:
        return None
    try:
        return round(int(amt) / 1_000_000, 6)
    except (TypeError, ValueError):
        return None


def _ts_ms(ms) -> str:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OSError, OverflowError):
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
