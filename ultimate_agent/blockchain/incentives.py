"""Economic incentive management with token-fiat conversion."""

from __future__ import annotations

import time
from typing import Dict, Any


class TokenFiatExchange:
    """Utility methods for converting between tokens and fiat."""

    TOKEN_TO_USD = 0.10  # 1 token = 0.10 USD for simulation

    @classmethod
    def tokens_to_fiat(cls, tokens: float, currency: str = "USD") -> float:
        return float(tokens) * cls.TOKEN_TO_USD

    @classmethod
    def fiat_to_tokens(cls, amount: float, currency: str = "USD") -> float:
        return float(amount) / cls.TOKEN_TO_USD

    @classmethod
    def update_rate(cls, new_rate: float) -> None:
        """Update the token to fiat conversion rate."""
        if new_rate <= 0:
            raise ValueError("rate must be positive")
        cls.TOKEN_TO_USD = float(new_rate)


class EconomyManager:
    """Track participant balances and distribute token rewards."""

    def __init__(self, blockchain_manager: Any):
        self.blockchain = blockchain_manager
        self.balances: Dict[str, float] = {}
        self.ledger: list[Dict[str, Any]] = []
        self.stakes: Dict[str, float] = {}
        self.stake_start: Dict[str, float] = {}
        self.apr: float = 0.10  # simple annual return

    def reward(self, participant_id: str, tokens: float, task_id: str) -> Dict[str, Any]:
        """Reward a participant and record the transaction."""
        self.balances[participant_id] = self.balances.get(participant_id, 0.0) + tokens
        tx_hash = None
        if self.blockchain:
            tx_hash = self.blockchain.send_earnings(tokens, task_id, currency="PAIN")
        record = {
            "participant": participant_id,
            "task_id": task_id,
            "tokens": tokens,
            "tx_hash": tx_hash,
            "timestamp": time.time(),
        }
        self.ledger.append(record)
        return record

    def get_balance(self, participant_id: str) -> float:
        """Get current token balance for participant."""
        return self.balances.get(participant_id, 0.0)

    def redeem_tokens(self, participant_id: str, tokens: float, currency: str = "USD") -> Dict[str, Any]:
        """Redeem tokens for fiat currency."""
        available = self.balances.get(participant_id, 0.0)
        if tokens > available:
            return {"success": False, "error": "insufficient_balance"}
        amount = TokenFiatExchange.tokens_to_fiat(tokens, currency)
        self.balances[participant_id] = available - tokens
        payout = {
            "success": True,
            "payout": amount,
            "currency": currency,
        }
        return payout

    def stake_tokens(self, participant_id: str, tokens: float) -> Dict[str, Any]:
        """Stake tokens to earn interest."""
        if tokens <= 0:
            return {"success": False, "error": "invalid_amount"}
        available = self.balances.get(participant_id, 0.0)
        if tokens > available:
            return {"success": False, "error": "insufficient_balance"}
        self.balances[participant_id] = available - tokens
        self.stakes[participant_id] = self.stakes.get(participant_id, 0.0) + tokens
        self.stake_start[participant_id] = time.time()
        return {"success": True, "staked": tokens}

    def unstake_tokens(self, participant_id: str) -> Dict[str, Any]:
        """Unstake tokens and collect interest based on staking duration."""
        tokens = self.stakes.pop(participant_id, 0.0)
        if tokens == 0:
            return {"success": False, "error": "no_stake"}
        start = self.stake_start.pop(participant_id, time.time())
        elapsed_days = max(0.0, (time.time() - start) / 86400)
        interest = tokens * self.apr * (elapsed_days / 365.0)
        total = tokens + interest
        self.balances[participant_id] = self.balances.get(participant_id, 0.0) + total
        return {"success": True, "unstaked": tokens, "interest": interest}

__all__ = ["TokenFiatExchange", "EconomyManager"]
