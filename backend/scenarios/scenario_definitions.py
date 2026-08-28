"""
The three replayable demo scenarios required by the brief. Each is a
scripted sequence of data_engine overrides -- the rest of the market keeps
moving organically (small random walk) around the scripted events, so the
demo looks like a live market, not a canned animation.

Cycle numbers are relative to when the scenario is loaded (scenario_step
starts at 0 in engine.py).
"""


def normal_market_scenario() -> dict:
    """Scenario 1: a clean, uneventful opportunity that goes through the
    whole pipeline without any friction -- proves the happy path end-to-end."""
    return {
        "name": "normal_market",
        "title": "Normal Market",
        "description": (
            "A calm market with good news for one company. Follow a single opportunity "
            "cleanly through the whole process: spotted, checked for safety, funded and traded."
        ),
        "duration_cycles": 10,
        "events": [
            {
                "cycle": 2, "asset": "INFY",
                "override": {
                    "price_change_pct": 0.028, "volatility": 0.013, "liquidity": 0.92,
                    "news": ["Company beats estimates with record profit and strong guidance"],
                    "event_tags": ["earnings"],
                },
                "annotation": "Scripted: strong earnings beat",
            },
        ],
    }


def market_shock_scenario() -> dict:
    """Scenario 2: a sudden geopolitical shock spikes volatility and drains
    liquidity on GOLD -- the regime should flip to CRISIS and the Risk
    Guardian should reject any new exposure, even if the agent is bullish."""
    return {
        "name": "market_shock",
        "title": "Sudden Price Shock",
        "description": (
            "A serious world event hits the gold market. Prices swing violently and it "
            "becomes hard to trade. Watch the system recognise the danger and refuse to "
            "open new positions even while it still sees a tempting price move."
        ),
        "duration_cycles": 12,
        "events": [
            {
                "cycle": 2, "asset": "GOLD",
                "override": {
                    "price_change_pct": 0.02, "volatility": 0.02, "liquidity": 0.8,
                    "news": ["Geopolitical tension building near key supply routes"],
                },
                "annotation": "Scripted: early warning signs",
            },
            {
                "cycle": 4, "asset": "GOLD",
                "override": {
                    "price_change_pct": 0.045, "volatility": 0.09, "liquidity": 0.15,
                    "news": ["Major geopolitical conflict escalates, trading halted amid crisis"],
                    "event_tags": ["geopolitical", "crisis"],
                },
                "annotation": "Scripted: sudden shock event",
            },
            {
                "cycle": 5, "asset": "GOLD",
                "override": {
                    "price_change_pct": 0.01, "volatility": 0.08, "liquidity": 0.2,
                    "news": ["Markets remain volatile after crisis escalation"],
                },
                "annotation": "Scripted: crisis regime persists",
            },
        ],
    }


def strategy_degradation_scenario() -> dict:
    """Scenario 3: TCS is pumped with a bullish signal, then reliably dumped
    for the next few cycles, several times in a row -- so the agent's BUY
    calls keep losing money. After enough losses land in the same regime,
    the Adaptation Engine should visibly cut confidence/size and tighten
    risk limits, and later pump cycles should produce smaller positions."""
    events = []
    repetitions = 4
    spacing = 7
    for r in range(repetitions):
        base = r * spacing
        events.append({
            "cycle": base, "asset": "TCS",
            "override": {
                "price_change_pct": 0.04, "volatility": 0.012, "liquidity": 0.85,
                "news": ["Company beats estimates with strong guidance"],
            },
            "annotation": f"Scripted: pump #{r+1} (looks bullish)",
        })
        events.append({
            "cycle": base + 1, "asset": "TCS",
            "override": {"price_change_pct": -0.02, "volatility": 0.012, "liquidity": 0.85},
            "annotation": f"Scripted: reversal #{r+1} begins",
        })
        events.append({
            "cycle": base + 2, "asset": "TCS",
            "override": {"price_change_pct": -0.02, "volatility": 0.014, "liquidity": 0.85},
            "annotation": f"Scripted: reversal #{r+1} continues",
        })
        events.append({
            "cycle": base + 3, "asset": "TCS",
            "override": {"price_change_pct": -0.015, "volatility": 0.014, "liquidity": 0.85},
            "annotation": f"Scripted: reversal #{r+1} confirms the loss",
        })

    return {
        "name": "strategy_degradation",
        "title": "Strategy Underperformance",
        "description": (
            "A stock repeatedly looks promising, gets bought, then falls and loses money. "
            "Watch the system notice the pattern in its own results and respond by becoming "
            "less confident, trading smaller and tightening its safety limits."
        ),
        "duration_cycles": repetitions * spacing + 3,
        "events": events,
    }


def liquidity_drop_scenario() -> dict:
    """Liquidity on CRUDE_OIL dries up while price barely moves. The regime
    should become LOW_LIQUIDITY and the Risk Guardian should halve or block
    trades because getting in and out becomes expensive."""
    return {
        "name": "liquidity_drop",
        "title": "Liquidity Drop",
        "description": (
            "Buyers and sellers disappear from the crude oil market while the price "
            "stays calm. The system should notice it can no longer trade cheaply and "
            "cut trade sizes or refuse to trade."
        ),
        "duration_cycles": 10,
        "events": [
            {"cycle": 2, "asset": "CRUDE_OIL",
             "override": {"price_change_pct": 0.004, "volatility": 0.018, "liquidity": 0.45},
             "annotation": "Scripted: liquidity starting to thin"},
            {"cycle": 3, "asset": "CRUDE_OIL",
             "override": {"price_change_pct": -0.003, "volatility": 0.02, "liquidity": 0.22},
             "annotation": "Scripted: liquidity drops below safe level"},
            {"cycle": 4, "asset": "CRUDE_OIL",
             "override": {"price_change_pct": 0.002, "volatility": 0.02, "liquidity": 0.18},
             "annotation": "Scripted: very hard to trade"},
            {"cycle": 5, "asset": "CRUDE_OIL",
             "override": {"price_change_pct": 0.001, "volatility": 0.019, "liquidity": 0.2},
             "annotation": "Scripted: thin market persists"},
        ],
    }


def negative_news_scenario() -> dict:
    """A company-specific bad-news event on TCS. The Equity Agent's news
    reading should turn negative and push it out of the position."""
    return {
        "name": "negative_news",
        "title": "Negative News",
        "description": (
            "A company announcement turns bad for TCS. Watch the Equity Agent read the "
            "news, turn negative on the asset, and move to cut the position."
        ),
        "duration_cycles": 10,
        "events": [
            {"cycle": 1, "asset": "TCS",
             "override": {"price_change_pct": 0.03, "volatility": 0.012, "liquidity": 0.9,
                          "news": ["Company beats estimates with strong guidance"]},
             "annotation": "Scripted: good news first, system buys in"},
            {"cycle": 3, "asset": "TCS",
             "override": {"price_change_pct": -0.025, "volatility": 0.022, "liquidity": 0.8,
                          "news": ["Regulator opens investigation, company issues profit warning"],
                          "event_tags": ["company_news"]},
             "annotation": "Scripted: bad news lands"},
            {"cycle": 4, "asset": "TCS",
             "override": {"price_change_pct": -0.03, "volatility": 0.028, "liquidity": 0.72,
                          "news": ["Analysts downgrade the stock after guidance cut"]},
             "annotation": "Scripted: downgrade follows"},
        ],
    }


def high_volatility_scenario() -> dict:
    """Broad, sustained choppiness across several assets (no crisis headline).
    The regime should sit in HIGH_VOLATILITY and the Risk Guardian should
    visibly halve position sizes on every approved trade."""
    events = []
    for c in range(1, 8):
        swing = 0.03 if c % 2 else -0.028
        events.append({
            "cycle": c, "asset": "INFY",
            "override": {"price_change_pct": swing, "volatility": 0.05, "liquidity": 0.7},
            "annotation": "Scripted: large price swings",
        })
        events.append({
            "cycle": c, "asset": "GOLD",
            "override": {"price_change_pct": -swing * 0.8, "volatility": 0.055, "liquidity": 0.65},
            "annotation": "Scripted: large price swings",
        })
    return {
        "name": "high_volatility",
        "title": "High Price Activity",
        "description": (
            "Prices swing sharply up and down across several assets without a crisis "
            "headline. The system should stay active but cut every trade size in half "
            "while conditions stay choppy."
        ),
        "duration_cycles": 10,
        "events": events,
    }


def concentration_limit_scenario() -> dict:
    """One asset keeps looking attractive, so the agent keeps wanting more of it.
    The Risk Guardian lets the first trade through, then MODIFIES the next one
    down to the room remaining under the single-asset cap, then REJECTS further
    buying entirely. This is the clearest demonstration that the AI proposes but
    does not decide."""
    events = [
        {
            "cycle": c, "asset": "INFY",
            "override": {
                "price_change_pct": 0.05, "volatility": 0.030, "liquidity": 1.0,
                "news": ["Company beats estimates with record profit and strong guidance and buyback"],
                "event_tags": ["earnings"],
            },
            "annotation": "Scripted: persistently strong buy signal",
        }
        for c in range(0, 9)
    ]
    return {
        "name": "concentration_limit",
        "title": "Safety Limit Reached",
        "description": (
            "One company keeps looking like a great buy, and the agent keeps asking for more "
            "of it. Watch the safety check allow the first trade, cut the second one down to "
            "the amount still permitted, and then refuse further buying to stop everything "
            "being staked on a single asset."
        ),
        "duration_cycles": 10,
        "events": events,
    }


def list_scenarios() -> list[dict]:
    return [
        normal_market_scenario(),
        market_shock_scenario(),
        concentration_limit_scenario(),
        liquidity_drop_scenario(),
        negative_news_scenario(),
        high_volatility_scenario(),
        strategy_degradation_scenario(),
    ]


def get_scenario(name: str) -> dict | None:
    for s in list_scenarios():
        if s["name"] == name:
            return s
    return None
