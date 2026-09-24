"""
Common types, exceptions and helpers shared by all live blockchain API
adapters (etherscan.py, tronscan.py).
"""
import re
from dataclasses import dataclass, asdict
from typing import Optional

ETH_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
TRON_ADDRESS_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")


class BlockchainAPIError(Exception):
    """
    Base class for every live-adapter failure. `reason` is short and safe
    to show directly in the UI/judge demo (never contains an API key).
    LIVE MODE callers catch this and fall back to a clear UI error instead
    of crashing or silently returning fake data.
    """
    def __init__(self, reason: str, code: str = "api_error"):
        super().__init__(reason)
        self.reason = reason
        self.code = code


class MissingAPIKeyError(BlockchainAPIError):
    def __init__(self, chain: str):
        super().__init__(f"No API key configured for {chain}.", code="missing_api_key")


class InvalidAddressError(BlockchainAPIError):
    def __init__(self, chain: str, address: str):
        super().__init__(f"'{address}' is not a valid {chain} address.", code="invalid_address")


class RateLimitError(BlockchainAPIError):
    def __init__(self, chain: str):
        super().__init__(f"{chain} API rate limit reached.", code="rate_limited")


class UpstreamTimeoutError(BlockchainAPIError):
    def __init__(self, chain: str):
        super().__init__(f"{chain} API request timed out.", code="timeout")


class UpstreamAPIError(BlockchainAPIError):
    def __init__(self, chain: str, detail: str):
        super().__init__(f"{chain} API returned an error: {detail}", code="upstream_error")


class NoTransactionsError(BlockchainAPIError):
    def __init__(self, chain: str, address: str):
        super().__init__(f"No transactions found on-chain for this {chain} address.", code="no_transactions")


def is_valid_ethereum_address(address: str) -> bool:
    return bool(ETH_ADDRESS_RE.match((address or "").strip()))


def is_valid_tron_address(address: str) -> bool:
    return bool(TRON_ADDRESS_RE.match((address or "").strip()))


@dataclass
class NormalizedTx:
    """The common transaction shape every adapter normalizes into."""
    chain: str
    tx_hash: str
    from_addr: str
    to_addr: str
    amount: float
    asset: str
    timestamp: str  # ISO 8601, UTC
    block_number: Optional[int]
    token_address: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        d["from"] = d.pop("from_addr")
        d["to"] = d.pop("to_addr")
        return d
