"""Test and example usage of the critic ensemble."""

from critic_ensemble import (
    CriticEnsemble,
    CriticVerdict,
    SamplerSetting,
    sampler_config,
    to_json,
)


def mock_critic(prompt: str, sampler: SamplerSetting) -> CriticVerdict:
    """Mock critic for testing. In production, this calls an LLM."""
    # Simulate different outputs based on sampler setting
    if sampler == SamplerSetting.CONSERVATIVE:
        return CriticVerdict(
            sampler=sampler,
            score=0.65,
            passed=False,
            blocking_issues=["Missing error handling", "No type hints"],
            suggestions=["Add docstrings"],
            reasoning="Strict rubric: code lacks robustness.",
        )
    elif sampler == SamplerSetting.BALANCED:
        return CriticVerdict(
            sampler=sampler,
            score=0.75,
            passed=True,
            blocking_issues=[],
            suggestions=["Consider edge cases"],
            reasoning="Balanced assessment: code is functional with minor improvements.",
        )
    else:  # CREATIVE
        return CriticVerdict(
            sampler=sampler,
            score=0.80,
            passed=True,
            blocking_issues=[],
            suggestions=[],
            reasoning="Creative lens: code solves the problem effectively.",
        )


def test_ensemble_consensus():
    """Test ensemble aggregation with mock critics."""
    ensemble = CriticEnsemble(mock_critic, acceptance_threshold=0.7, agreement_threshold=0.66)

    result = ensemble.evaluate(
        task_context="Write a Python function to sort a list.",
        candidate="def sort_list(items: list) -> list:\n    return sorted(items)",
    )

    print("=== Critic Ensemble Results ===")
    print(f"Consensus Score: {result.consensus_score:.2f}")
    print(f"Consensus Passed: {result.consensus_passed}")
    print(f"Agreement Level: {result.agreement_level:.2f}")
    print(f"Recommendation: {result.recommendation}")
    print(f"Blocking Issues: {result.blocking_issues}")
    print(f"Suggestions: {result.suggestions}")
    print(f"\nAccept Candidate: {ensemble.should_accept(result)}")

    print("\n=== Individual Verdicts ===")
    for v in result.verdicts:
        print(f"{v.sampler.value:12s}: score={v.score:.2f}, passed={v.passed}, reasoning={v.reasoning}")

    print("\n=== Full JSON ===")
    print(to_json(result))


def test_sampler_configs():
    """Verify sampler configs are correctly defined."""
    for sampler in SamplerSetting:
        config = sampler_config(sampler)
        print(f"{sampler.value}: {config}")


if __name__ == "__main__":
    test_ensemble_consensus()
    print("\n" + "="*50 + "\n")
    test_sampler_configs()
