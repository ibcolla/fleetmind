"""
FleetMind — Centralized LLM Telemetry & Pricing Module
------------------------------------------------------
Calculates inference token costs and formats telemetry for Nebius Token Factory
and OpenAI-compatible models.
"""

from typing import Dict, Any

# Model pricing registry per 1,000,000 tokens (USD)
# Grounded in Nebius Token Factory pricing structure (September 2026)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "nvidia/nemotron-3-super-120b-a12b": {
        "input_cost_per_1m": 0.30,
        "output_cost_per_1m": 0.90,
    },
    "default": {
        "input_cost_per_1m": 0.30,
        "output_cost_per_1m": 0.90,
    },
}


def calculate_inference_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Calculate estimated USD inference cost based on model pricing per 1M tokens.

    Args:
        model: Model identifier string (e.g. 'nvidia/nemotron-3-super-120b-a12b').
        input_tokens: Number of prompt/input tokens.
        output_tokens: Number of completion/output tokens.

    Returns:
        Estimated USD cost rounded to 6 decimal places.
    """
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    input_cost = (max(0, input_tokens) / 1_000_000.0) * pricing["input_cost_per_1m"]
    output_cost = (max(0, output_tokens) / 1_000_000.0) * pricing["output_cost_per_1m"]
    return round(input_cost + output_cost, 6)
