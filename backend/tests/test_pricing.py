"""
Unit tests for Nebius Token Factory pricing and cost calculation module.
"""

from api.pricing import calculate_inference_cost, MODEL_PRICING


def test_nemotron_3_super_pricing():
    """Verify exact estimated cost for nvidia/nemotron-3-super-120b-a12b ($0.30/1M in, $0.90/1M out)."""
    model = "nvidia/nemotron-3-super-120b-a12b"
    
    # Test benchmark specific token counts: 382 input, 236 output
    # (382 / 1M * 0.30) + (236 / 1M * 0.90) = 0.0001146 + 0.0002124 = 0.000327
    cost = calculate_inference_cost(model, 382, 236)
    assert cost == 0.000327

    # Test 1M input, 1M output tokens
    cost_1m = calculate_inference_cost(model, 1_000_000, 1_000_000)
    assert cost_1m == 1.20


def test_unknown_model_fallback():
    """Verify fallback pricing for unknown models."""
    cost = calculate_inference_cost("unknown/model-name", 1_000_000, 1_000_000)
    assert cost == 1.20


def test_zero_tokens():
    """Verify zero token cost handling."""
    cost = calculate_inference_cost("nvidia/nemotron-3-super-120b-a12b", 0, 0)
    assert cost == 0.0
