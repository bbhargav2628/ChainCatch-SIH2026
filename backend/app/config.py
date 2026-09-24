"""
LIVE MODE settings, loaded from backend/.env (see .env.example).
None of these values are ever sent to the React frontend.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass  # python-dotenv not installed — fall back to real environment variables only


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "").strip()
TRONSCAN_API_KEY = os.getenv("TRONSCAN_API_KEY", "").strip()

MAX_HOPS = _int_env("MAX_HOPS", 4)
MAX_WALLETS = _int_env("MAX_WALLETS", 100)
MAX_TRANSACTIONS_PER_WALLET = _int_env("MAX_TRANSACTIONS_PER_WALLET", 100)
CACHE_TTL_SECONDS = _int_env("CACHE_TTL_SECONDS", 300)
REQUEST_TIMEOUT_SECONDS = _int_env("REQUEST_TIMEOUT_SECONDS", 10)
