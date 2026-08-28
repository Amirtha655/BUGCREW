"""
AI provider interface.

Important design decision: the provider NEVER decides the action, confidence,
or allocation amount. Those numbers come from the deterministic scoring
engine in each agent (base_agent.py) so the money-moving decision is always
auditable and reproducible. The provider's only job is to turn the computed
numbers + raw market data into a clear natural-language explanation
(the "reasoning", "factors", "risk_factors" text). This keeps the system
honest: an LLM (or its absence) can never change what the system actually
does, only how it explains what it already decided.

Any provider must never raise past this interface -- callers wrap calls in
a try/except and fall back to the rule-based templated text on any failure,
so the demo keeps working even if an API key is missing or a network call
times out.
"""
from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    def enrich(
        self,
        *,
        event: Any,
        market_type: Any,
        signals: dict,
        rule_based: dict,
        regime: Any,
        memory_hint: dict,
    ) -> dict:
        """Return {"reasoning": str, "factors": [str], "risk_factors": [str]}."""
        raise NotImplementedError


def get_provider() -> AIProvider:
    from config import settings
    from ai.rule_based_provider import RuleBasedProvider
    from ai.llm_provider import GroqProvider

    if settings.ai_provider == "groq":
        return GroqProvider()
    return RuleBasedProvider()
