"""Tests for DeepConf reasoning utilities."""

import math

from app.deepconf import (
    ReasoningTrace,
    OfflineDeepConf,
    calculate_group_confidence,
    calculate_token_confidence,
    bottom_10_percent_confidence,
    lowest_group_confidence,
    tail_confidence,
)


def test_token_confidence() -> None:
    """Token confidence uses negative average log-probability."""
    logprobs = [-1.0, -2.0, -3.0]
    confidence = calculate_token_confidence(logprobs, top_k=3)
    assert math.isclose(confidence, 2.0)


def test_group_confidence() -> None:
    """Sliding window confidence is averaged correctly."""
    token_confidences = [1.0, 2.0, 3.0]
    groups = calculate_group_confidence(token_confidences, window_size=2)
    assert groups == [1.5, 2.5]


def test_advanced_confidence_metrics() -> None:
    """Verify higher-level confidence metrics."""
    tokens = [[-1.0, -2.0], [-1.0, -2.0], [-3.0, -4.0]]
    assert math.isclose(lowest_group_confidence(tokens, window_size=2), 1.5)
    assert math.isclose(bottom_10_percent_confidence(tokens, window_size=2), 1.5)
    assert math.isclose(tail_confidence(tokens, tail_size=2), 2.5)


def test_weighted_voting_and_filtering() -> None:
    """Ensure filtering keeps top traces and voting uses weights."""
    traces = [
        ReasoningTrace(text="", tokens=[], logprobs=[], confidence=0.9, answer="A"),
        ReasoningTrace(text="", tokens=[], logprobs=[], confidence=0.5, answer="B"),
        ReasoningTrace(text="", tokens=[], logprobs=[], confidence=0.8, answer="A"),
    ]
    deepconf = OfflineDeepConf(model_name="dummy")
    filtered = deepconf.confidence_filtering(traces, top_percent=0.5)
    assert len(filtered) == 1
    answer = deepconf.weighted_majority_voting(traces)
    assert answer == "A"
