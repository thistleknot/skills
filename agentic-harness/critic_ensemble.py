"""Critic agent ensemble for agentic harness.

Implements multi-critic evaluation for difficult problems using three sampler
settings (conservative, balanced, creative) to reduce single-critic bias and
improve decision quality through aggregated feedback.
"""

from dataclasses import dataclass
from enum import Enum
import json
from typing import Any, Callable, Optional


class SamplerSetting(Enum):
    """Sampler setting profiles for critic agents."""
    CONSERVATIVE = "conservative"      # Low temp, strict rubric, risk-averse
    BALANCED = "balanced"               # Default settings, moderate
    CREATIVE = "creative"               # Higher temp, permissive rubric, exploratory


@dataclass
class CriticVerdict:
    """Structured feedback from a single critic."""
    sampler: SamplerSetting
    score: float                         # [0.0, 1.0]
    passed: bool                         # score >= threshold
    blocking_issues: list[str]          # Must-fix items
    suggestions: list[str]              # Nice-to-have items
    reasoning: str                      # Justification


@dataclass
class AggregatedVerdictResult:
    """Aggregated critique from all critics."""
    consensus_score: float              # Average or median of scores
    consensus_passed: bool              # Majority vote on pass/fail
    verdicts: list[CriticVerdict]       # All individual verdicts
    agreement_level: float              # [0.0, 1.0] - how aligned critics were
    blocking_issues: list[str]          # Union of all blocking issues
    suggestions: list[str]              # Deduplicated suggestions
    recommendation: str                 # "ACCEPT", "REVISE", "ESCALATE"
    disposition: dict[str, Any]         # Metadata for human review


class CriticEnsemble:
    """Multi-critic evaluation harness."""

    def __init__(
        self,
        critic_fn: Callable[[str, SamplerSetting], CriticVerdict],
        acceptance_threshold: float = 0.7,
        agreement_threshold: float = 0.66,  # 2/3 consensus
    ):
        """
        Require: critic_fn is a callable(task_context, sampler_setting) -> CriticVerdict.
        Guarantee: All critic calls execute in parallel (or sequential, per caller); aggregated result is always returned.
        Maintain: All verdicts are preserved; no information is lost in aggregation.
        """
        self.critic_fn = critic_fn
        self.acceptance_threshold = acceptance_threshold
        self.agreement_threshold = agreement_threshold

    def evaluate(self, task_context: str, candidate: str) -> AggregatedVerdictResult:
        """
        Run all three critics on the candidate.

        Require: task_context is the problem statement; candidate is the solution to evaluate.
        Guarantee: Returns aggregated verdict with all three individual verdicts preserved.
        Maintain: Aggregation is deterministic and reproducible.
        """
        verdicts: list[CriticVerdict] = []

        # Launch critics at three sampler settings
        for sampler in SamplerSetting:
            prompt = f"{task_context}\n\nCandidate:\n{candidate}"
            verdict = self.critic_fn(prompt, sampler)
            verdicts.append(verdict)

        # Compute aggregated metrics
        scores = [v.score for v in verdicts]
        consensus_score = sum(scores) / len(scores)
        consensus_passed = sum(1 for v in verdicts if v.passed) >= len(verdicts) * self.agreement_threshold

        # Measure agreement: if all critics have the same pass/fail, agreement_level = 1.0
        pass_count = sum(1 for v in verdicts if v.passed)
        agreement_level = max(pass_count, len(verdicts) - pass_count) / len(verdicts)

        # Aggregate all blocking issues and deduplicate suggestions
        all_blocking = []
        all_suggestions = []
        for v in verdicts:
            all_blocking.extend(v.blocking_issues)
            all_suggestions.extend(v.suggestions)

        blocking_issues = list(set(all_blocking))
        suggestions = list(set(all_suggestions))

        # Determine recommendation
        if consensus_passed and agreement_level >= self.agreement_threshold:
            recommendation = "ACCEPT"
        elif agreement_level < 0.5:
            recommendation = "ESCALATE"  # High disagreement, needs human input
        else:
            recommendation = "REVISE"  # Majority suggests revision

        # Build disposition metadata
        disposition = {
            "sampler_scores": {v.sampler.value: v.score for v in verdicts},
            "disagreement_detail": [
                {"sampler": v.sampler.value, "passed": v.passed} for v in verdicts
            ],
            "blocking_count": len(blocking_issues),
            "suggestion_count": len(suggestions),
        }

        return AggregatedVerdictResult(
            consensus_score=consensus_score,
            consensus_passed=consensus_passed,
            verdicts=verdicts,
            agreement_level=agreement_level,
            blocking_issues=blocking_issues,
            suggestions=suggestions,
            recommendation=recommendation,
            disposition=disposition,
        )

    def should_accept(self, aggregated: AggregatedVerdictResult) -> bool:
        """
        Determine if candidate should be accepted based on aggregated verdict.

        Returns True only if consensus_passed and agreement_level meets threshold.
        """
        return (
            aggregated.consensus_passed
            and aggregated.agreement_level >= self.agreement_threshold
        )


def sampler_config(sampler: SamplerSetting) -> dict[str, Any]:
    """
    Get agent settings for a specific sampler profile.

    Returns overrides to apply to default_agent_settings.json.
    """
    configs = {
        SamplerSetting.CONSERVATIVE: {
            "temperature": 0.0,      # Deterministic
            "top_p": 0.8,            # Narrow sampling
            "frequency_penalty": 0.9,  # Suppress repetition
            "verification_passes": 1,  # Self-critique enabled
            "abstention_policy": "exclude_if_low",  # Risk-averse
        },
        SamplerSetting.BALANCED: {
            "temperature": 0.7,
            "top_p": 0.9,
            "frequency_penalty": 0.7,
            "verification_passes": 0,
            "abstention_policy": "exclude_if_low",
        },
        SamplerSetting.CREATIVE: {
            "temperature": 1.0,      # High entropy
            "top_p": 0.95,           # Broader sampling
            "frequency_penalty": 0.5,  # Allow repetition
            "verification_passes": 0,  # Skip self-critique
            "abstention_policy": "include_all",  # Permissive
        },
    }
    return configs[sampler]


def to_json(result: AggregatedVerdictResult) -> str:
    """Serialize aggregated verdict to JSON for logging."""
    data = {
        "consensus_score": result.consensus_score,
        "consensus_passed": result.consensus_passed,
        "agreement_level": result.agreement_level,
        "recommendation": result.recommendation,
        "blocking_issues": result.blocking_issues,
        "suggestions": result.suggestions,
        "disposition": result.disposition,
        "verdicts": [
            {
                "sampler": v.sampler.value,
                "score": v.score,
                "passed": v.passed,
                "blocking_issues": v.blocking_issues,
                "suggestions": v.suggestions,
                "reasoning": v.reasoning,
            }
            for v in result.verdicts
        ],
    }
    return json.dumps(data, indent=2)
