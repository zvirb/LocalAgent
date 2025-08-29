"""DeepConf reasoning utilities for Ollama models."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional

import ollama


# ---------------------------------------------------------------------------
# Confidence Metrics
# ---------------------------------------------------------------------------


def calculate_token_confidence(logprobs: List[float], top_k: int = 20) -> float:
    """Calculate token confidence from log-probabilities.

    Args:
        logprobs: Log-probabilities for top tokens at this position.
        top_k: Number of probabilities to consider.

    Returns:
        Confidence score where higher values indicate more peaked distribution.
    """

    if not logprobs:
        return 0.0
    k = min(top_k, len(logprobs))
    return -sum(logprobs[:k]) / k


def calculate_group_confidence(
    token_confidences: List[float], window_size: int = 2048
) -> List[float]:
    """Calculate confidence over sliding windows of tokens."""

    if not token_confidences:
        return []
    groups: List[float] = []
    for i in range(len(token_confidences) - window_size + 1):
        group_conf = sum(token_confidences[i : i + window_size]) / window_size
        groups.append(group_conf)
    return groups


def lowest_group_confidence(
    trace_tokens: List[List[float]], window_size: int = 2048
) -> float:
    """Return the minimum confidence across all token groups."""

    token_confidences = [calculate_token_confidence(t) for t in trace_tokens]
    group_confidences = calculate_group_confidence(token_confidences, window_size)
    return min(group_confidences) if group_confidences else 0.0


def bottom_10_percent_confidence(
    trace_tokens: List[List[float]], window_size: int = 2048
) -> float:
    """Average confidence of the bottom 10% groups."""

    token_confidences = [calculate_token_confidence(t) for t in trace_tokens]
    group_confidences = calculate_group_confidence(token_confidences, window_size)
    if not group_confidences:
        return 0.0
    sorted_groups = sorted(group_confidences)
    bottom_10_count = max(1, len(sorted_groups) // 10)
    bottom_10 = sorted_groups[:bottom_10_count]
    return sum(bottom_10) / len(bottom_10)


def tail_confidence(trace_tokens: List[List[float]], tail_size: int = 2048) -> float:
    """Confidence of the final portion of the trace."""

    if not trace_tokens:
        return 0.0
    tail_tokens = trace_tokens[-tail_size:]
    token_confidences = [calculate_token_confidence(t) for t in tail_tokens]
    return sum(token_confidences) / len(token_confidences)


# ---------------------------------------------------------------------------
# DeepConf Core Classes
# ---------------------------------------------------------------------------


@dataclass
class ReasoningTrace:
    """Container for a single reasoning trace."""

    text: str
    tokens: List[str]
    logprobs: List[List[float]]
    confidence: float
    answer: str


class DeepConfOllama:
    """Base DeepConf integration for Ollama models."""

    def __init__(
        self, model_name: str, window_size: int = 2048, client: Optional[Any] = None
    ) -> None:
        self.model = model_name
        self.window_size = window_size
        self.client = client or ollama.Client()

    # ------------------------------------------------------------------
    # Trace generation utilities
    # ------------------------------------------------------------------
    def generate_trace(self, prompt: str, temperature: float = 0.6) -> ReasoningTrace:
        """Generate a single reasoning trace with estimated confidence."""

        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            options={
                "temperature": temperature,
                "top_p": 0.95,
                "num_predict": 8192,
                "raw": True,
            },
        )

        text = response.get("response", "")
        answer = self.extract_answer(text)
        confidence = self.estimate_confidence(text)

        return ReasoningTrace(
            text=text,
            tokens=text.split(),
            logprobs=[],  # Ollama client does not expose logprobs
            confidence=confidence,
            answer=answer,
        )

    # ------------------------------------------------------------------
    # Confidence utilities
    # ------------------------------------------------------------------
    def extract_answer(self, text: str) -> str:
        """Extract a final answer from model output."""

        for line in reversed(text.strip().splitlines()):
            if line.strip():
                return line.strip()
        return ""

    def estimate_confidence(self, text: str) -> float:
        """Estimate confidence heuristically from output text."""

        confidence = 1.0
        text_lower = text.lower()

        uncertainty_phrases = [
            "i'm not sure",
            "perhaps",
            "maybe",
            "might be",
            "could be",
            "possibly",
            "i think",
            "probably",
        ]
        for phrase in uncertainty_phrases:
            if phrase in text_lower:
                confidence *= 0.8

        reasoning_markers = [
            "therefore",
            "thus",
            "hence",
            "clearly",
            "definitively",
            "certainly",
            "the answer is",
        ]
        for marker in reasoning_markers:
            if marker in text_lower:
                confidence *= 1.1

        if "wait" in text_lower or "actually" in text_lower:
            confidence *= 0.7

        return min(max(confidence, 0.0), 1.0)

    def calculate_trace_confidence(self, trace: ReasoningTrace) -> float:
        """Calculate confidence metrics for a full trace."""

        return self.estimate_confidence(trace.text)

    def calculate_window_confidence(self, tokens: List[str]) -> float:
        """Calculate confidence over a window of tokens."""

        token_confidences = [self.estimate_confidence(tok) for tok in tokens]
        if not token_confidences:
            return 0.0
        return sum(token_confidences) / len(token_confidences)

    async def stream_tokens(self, prompt: str) -> AsyncIterator[str]:
        """Stream tokens from Ollama.

        Ollama's Python client yields chunks of text; this method converts
        them into an async iterator of tokens.
        """

        iterator = self.client.generate(
            model=self.model,
            prompt=prompt,
            options={"temperature": 0.6, "top_p": 0.95},
            stream=True,
        )
        for chunk in iterator:
            text = chunk.get("response", "")
            if not text:
                continue
            for token in text.split():
                yield token

    def weighted_majority_voting(self, traces: List[ReasoningTrace]) -> str:
        """Perform confidence-weighted voting across traces."""
        vote_weights: Dict[str, float] = {}
        for trace in traces:
            vote_weights.setdefault(trace.answer, 0.0)
            vote_weights[trace.answer] += trace.confidence
        return max(vote_weights.items(), key=lambda x: x[1])[0]


class OfflineDeepConf(DeepConfOllama):
    """Offline confidence filtering and weighted voting."""

    def generate_multiple_traces(
        self, prompt: str, n_traces: int = 512
    ) -> List[ReasoningTrace]:
        traces = []
        for _ in range(n_traces):
            trace = self.generate_trace(prompt)
            traces.append(trace)
        return traces

    def confidence_filtering(
        self, traces: List[ReasoningTrace], top_percent: float = 0.1
    ) -> List[ReasoningTrace]:
        sorted_traces = sorted(traces, key=lambda x: x.confidence, reverse=True)
        keep_count = max(1, int(len(sorted_traces) * top_percent))
        return sorted_traces[:keep_count]

    def solve(
        self, prompt: str, n_traces: int = 512, filter_percent: float = 0.1
    ) -> tuple[str, List[ReasoningTrace]]:
        traces = self.generate_multiple_traces(prompt, n_traces)
        for trace in traces:
            trace.confidence = self.calculate_trace_confidence(trace)
        filtered = self.confidence_filtering(traces, filter_percent)
        answer = self.weighted_majority_voting(filtered)
        return answer, filtered


class OnlineDeepConf(DeepConfOllama):
    """Online confidence-based early stopping."""

    def __init__(self, model_name: str, window_size: int = 2048) -> None:
        super().__init__(model_name, window_size)
        self.warmup_size = 16
        self.consensus_threshold = 0.95

    def warmup_phase(self, prompt: str) -> tuple[float, List[ReasoningTrace]]:
        warmup_traces: List[ReasoningTrace] = []
        for _ in range(self.warmup_size):
            trace = self.generate_trace(prompt)
            trace.confidence = self.calculate_trace_confidence(trace)
            warmup_traces.append(trace)
        sorted_traces = sorted(warmup_traces, key=lambda x: x.confidence)
        threshold_index = int(0.9 * len(sorted_traces))
        threshold = sorted_traces[threshold_index].confidence
        return threshold, warmup_traces

    async def generate_with_early_stopping(
        self, prompt: str, threshold: float
    ) -> ReasoningTrace:
        current_text = ""
        current_tokens: List[str] = []
        recent_confidence = 1.0
        async for token in self.stream_tokens(prompt):
            current_text += token + " "
            current_tokens.append(token)
            if len(current_tokens) >= self.window_size:
                recent_confidence = self.calculate_window_confidence(
                    current_tokens[-self.window_size :]
                )
                if recent_confidence < threshold:
                    break
        answer = self.extract_answer(current_text)
        return ReasoningTrace(
            text=current_text,
            tokens=current_tokens,
            logprobs=[],
            confidence=recent_confidence,
            answer=answer,
        )

    async def solve_adaptive(
        self, prompt: str, max_traces: int = 512
    ) -> tuple[str, List[ReasoningTrace]]:
        threshold, traces = self.warmup_phase(prompt)
        while len(traces) < max_traces:
            new_trace = await self.generate_with_early_stopping(prompt, threshold)
            traces.append(new_trace)
            if self.check_consensus(traces):
                break
        return self.weighted_majority_voting(traces), traces

    def check_consensus(self, traces: List[ReasoningTrace]) -> bool:
        vote_weights: Dict[str, float] = {}
        total_weight = 0.0
        for trace in traces:
            vote_weights.setdefault(trace.answer, 0.0)
            vote_weights[trace.answer] += trace.confidence
            total_weight += trace.confidence
        max_weight = max(vote_weights.values())
        return (max_weight / total_weight) >= self.consensus_threshold


# ---------------------------------------------------------------------------
# Practical Implementation
# ---------------------------------------------------------------------------


class PracticalDeepConfOllama:
    """Practical DeepConf implementation using available Ollama features."""

    def __init__(self, model_name: str = "llama3.1:8b") -> None:
        self.model = model_name
        self.client = ollama.Client()

    def extract_final_answer(self, text: str) -> str:
        for line in reversed(text.strip().splitlines()):
            if line.strip():
                return line.strip()
        return ""

    def estimate_trace_confidence(self, text: str) -> float:
        base = DeepConfOllama(self.model)
        return base.estimate_confidence(text)

    def generate_reasoning_trace(
        self, problem: str, temperature: float = 0.6
    ) -> Dict[str, Any]:
        prompt = (
            "Please solve this step by step, showing all your reasoning.\n\n"
            f"Problem: {problem}\n\nSolution (think step by step):\n"
        )
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            options={
                "temperature": temperature,
                "top_p": 0.95,
                "max_tokens": 8192,
            },
        )
        text = response.get("response", "")
        answer = self.extract_final_answer(text)
        confidence = self.estimate_trace_confidence(text)
        return {"text": text, "answer": answer, "confidence": confidence}

    def parallel_reasoning(
        self, problem: str, n_samples: int = 32
    ) -> List[Dict[str, Any]]:
        traces = []
        for i in range(n_samples):
            temp = 0.6 + (i % 5) * 0.05
            trace = self.generate_reasoning_trace(problem, temp)
            traces.append(trace)
        return traces

    def apply_deepconf(
        self, problem: str, n_samples: int = 32, top_percent: float = 0.1
    ) -> Dict[str, Any]:
        traces = self.parallel_reasoning(problem, n_samples)
        sorted_traces = sorted(traces, key=lambda x: x["confidence"], reverse=True)
        keep_count = max(1, int(len(sorted_traces) * top_percent))
        filtered_traces = sorted_traces[:keep_count]
        answer_weights: Dict[str, float] = {}
        for trace in filtered_traces:
            answer = trace["answer"]
            answer_weights.setdefault(answer, 0.0)
            answer_weights[answer] += trace["confidence"]
        if answer_weights:
            final_answer = max(answer_weights.items(), key=lambda x: x[1])[0]
            final_conf = answer_weights[final_answer] / len(filtered_traces)
        else:
            final_answer = filtered_traces[0]["answer"] if filtered_traces else None
            final_conf = 0.0
        return {
            "answer": final_answer,
            "confidence": final_conf,
            "total_traces": n_samples,
            "filtered_traces": len(filtered_traces),
        }


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class DeepConfConfig:
    """Configuration defaults for DeepConf."""

    TEMPERATURE = 0.6
    TOP_P = 0.95
    MAX_TOKENS = 8192
    WINDOW_SIZE = 2048
    WARMUP_SIZE = 16
    FILTER_TOP_10 = 0.1
    FILTER_TOP_90 = 0.9
    CONSENSUS_THRESHOLD = 0.95
    MAX_TRACES = 512


MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "llama3.1:8b": {
        "temperature": 0.6,
        "top_p": 0.95,
        "window_size": 2048,
    },
    "qwen2.5:32b": {
        "temperature": 0.6,
        "top_p": 0.95,
        "window_size": 2048,
    },
    "deepseek-r1:8b": {
        "temperature": 0.6,
        "top_p": 0.95,
        "window_size": 2048,
    },
}
