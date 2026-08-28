"""
Groq-backed provider (free API, OpenAI-compatible endpoint).

Used only to rewrite the reasoning/factors/risk_factors into more natural
language, grounded strictly in the already-computed numbers. On any error
(no key, network failure, bad JSON) it silently falls back to the rule-based
templated text so the live demo never breaks because of an API hiccup.
"""
import json
import httpx
from ai.provider_interface import AIProvider
from ai.rule_based_provider import RuleBasedProvider
from config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are a financial market analysis assistant. A deterministic, "
    "risk-controlled trading system has ALREADY computed a decision (action, "
    "confidence, allocation). Your only job is to explain WHY that decision "
    "makes sense, using ONLY the facts given to you. Never propose a different "
    "action, never invent numbers, never mention information not provided. "
    "Respond with strict JSON only, no markdown: "
    '{"reasoning": "2-4 sentences", "factors": ["short bullet", ...max 4], '
    '"risk_factors": ["short bullet", ...max 3]}'
)


class GroqProvider(AIProvider):
    name = "groq"

    def __init__(self):
        self._fallback = RuleBasedProvider()

    def enrich(self, *, event, market_type, signals, rule_based, regime, memory_hint) -> dict:
        if not settings.groq_api_key:
            return self._fallback.enrich(
                event=event, market_type=market_type, signals=signals,
                rule_based=rule_based, regime=regime, memory_hint=memory_hint,
            )
        try:
            prompt = self._build_prompt(event, market_type, rule_based, regime, memory_hint)
            resp = httpx.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": settings.groq_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.4,
                    # gpt-oss models spend tokens on internal reasoning before
                    # emitting the answer, so a small budget makes them hit the
                    # cap mid-JSON and the request fails. Keep headroom and ask
                    # for low reasoning effort to stay ~1s per call.
                    "max_tokens": 1200,
                    "reasoning_effort": "low",
                    "response_format": {"type": "json_object"},
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(content)

            reasoning = str(data.get("reasoning") or rule_based["reasoning"])[:1200]
            factors = [str(f) for f in data.get("factors", [])][:4] or rule_based["factors"]
            risk_factors = [str(f) for f in data.get("risk_factors", [])][:3] or rule_based["risk_factors"]
            return {"reasoning": reasoning, "factors": factors, "risk_factors": risk_factors, "provider_used": "groq"}
        except Exception:
            return self._fallback.enrich(
                event=event, market_type=market_type, signals=signals,
                rule_based=rule_based, regime=regime, memory_hint=memory_hint,
            )

    def _build_prompt(self, event, market_type, rule_based, regime, memory_hint) -> str:
        news = ", ".join(event.news) if event.news else "none"
        return (
            f"Asset: {event.asset} ({market_type.value})\n"
            f"Price: {event.price}, change: {event.price_change_pct * 100:.2f}%\n"
            f"Volatility: {event.volatility:.3f}, Liquidity: {event.liquidity:.2f}\n"
            f"Market regime: {regime.value}\n"
            f"News/events: {news}\n"
            f"Computed decision (final, do not change): action={rule_based['action']}, "
            f"confidence={rule_based['confidence']:.2f}, allocation={rule_based['suggested_allocation']:.0f}, "
            f"strategy={rule_based['strategy_tag']}\n"
            f"Strategy's past performance in this regime: {memory_hint.get('summary', 'no history yet')}\n"
            f"Computed factors: {', '.join(rule_based['factors']) if rule_based['factors'] else 'none'}\n"
        )
