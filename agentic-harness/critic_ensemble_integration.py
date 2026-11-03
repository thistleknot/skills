"""Integration example: how to use critic ensemble in agentic-harness workflows.

This shows how to wire the critic ensemble into a harness that needs high-quality
decisions for difficult problems.
"""

from critic_ensemble import CriticEnsemble, CriticVerdict, SamplerSetting, sampler_config
from typing import Any, Callable, Optional


def integrate_critic_ensemble(
    harness_config: dict[str, Any],
    difficult_problem: bool = False,
) -> dict[str, Any]:
    """
    Integrate critic ensemble into harness routing.

    If difficult_problem=True, the harness will launch three critics before finalizing changes.
    Otherwise, uses single-pass validation.

    Example:
        config = {
            "task": "Generate API handler for user auth",
            "use_critics": True,
        }
        config = integrate_critic_ensemble(config, difficult_problem=True)
        # Now config includes critic_enabled, critic_threshold, etc.
    """
    if not difficult_problem:
        harness_config["critic_enabled"] = False
        return harness_config

    harness_config["critic_enabled"] = True
    harness_config["critic_config"] = {
        "acceptance_threshold": 0.7,
        "agreement_threshold": 0.66,
        "sampler_profiles": {
            "conservative": sampler_config(SamplerSetting.CONSERVATIVE),
            "balanced": sampler_config(SamplerSetting.BALANCED),
            "creative": sampler_config(SamplerSetting.CREATIVE),
        },
    }
    return harness_config


class AgenticHarnessWithCritics:
    """Example harness integration with critic ensemble."""

    def __init__(self, critic_fn: Callable[[str, SamplerSetting], CriticVerdict]):
        """Initialize harness with a critic function (typically an LLM call)."""
        self.ensemble = CriticEnsemble(critic_fn)
        self.critic_enabled = False
        self.run_log = []

    def route_decision(
        self,
        task_context: str,
        candidate_solution: str,
        difficult_problem: bool = False,
    ) -> dict[str, Any]:
        """
        Route a decision through critic ensemble if enabled.

        Returns:
            {
                "recommendation": "ACCEPT" | "REVISE" | "ESCALATE",
                "verdict": AggregatedVerdictResult or None,
                "can_proceed": bool,
            }
        """
        if not difficult_problem:
            return {
                "recommendation": "ACCEPT",
                "verdict": None,
                "can_proceed": True,
                "mode": "single_pass",
            }

        # Evaluate with critic ensemble
        verdict = self.ensemble.evaluate(task_context, candidate_solution)

        # Log for traceability
        self.run_log.append(
            {
                "task": task_context[:100],  # Truncate for log
                "recommendation": verdict.recommendation,
                "consensus_score": verdict.consensus_score,
            }
        )

        return {
            "recommendation": verdict.recommendation,
            "verdict": verdict,
            "can_proceed": self.ensemble.should_accept(verdict),
            "mode": "critic_ensemble",
        }


# Example usage pattern
def example_workflow():
    """Show how to use critic ensemble in a typical workflow."""

    def mock_critic_fn(prompt: str, sampler: SamplerSetting) -> CriticVerdict:
        """Mock critic. In production, call an LLM."""
        return CriticVerdict(
            sampler=sampler,
            score=0.75,
            passed=True,
            blocking_issues=[],
            suggestions=["Add tests"],
            reasoning=f"Using {sampler.value} setting.",
        )

    harness = AgenticHarnessWithCritics(mock_critic_fn)

    # Easy task: skip critics
    easy_result = harness.route_decision(
        task_context="Sort a list.",
        candidate_solution="sorted(items)",
        difficult_problem=False,
    )
    print(f"Easy task: {easy_result['recommendation']} (mode={easy_result['mode']})")

    # Hard task: use critics
    hard_result = harness.route_decision(
        task_context="Design a distributed cache invalidation protocol.",
        candidate_solution="Multi-layer TTL with eventual consistency.",
        difficult_problem=True,
    )
    print(f"Hard task: {hard_result['recommendation']} (mode={hard_result['mode']})")
    print(f"Can proceed: {hard_result['can_proceed']}")


if __name__ == "__main__":
    example_workflow()
