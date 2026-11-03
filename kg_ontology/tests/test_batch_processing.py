"""
Unit tests for batch triplet processing.

Tests the complete pipeline:
- Batch augmentation for multiple triplets
- Batch prompt building
- Batch enrichment with synset selection
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from batch_processing import (
    BatchAugmentationResult,
    BatchEnrichmentResult,
    BatchSynsetOrchestrator,
    BatchSelectionPromptBuilder,
)
from synset_selection_schema import (
    ElementSynsetChoices,
    TripletWithChosenSynsets,
)


@pytest.fixture
def orchestrator():
    """Initialize batch orchestrator."""
    return BatchSynsetOrchestrator(word2vec_model=None, k_neighbors=5)


@pytest.fixture
def sample_triplets():
    """Sample extracted triplets (multiple triplets from 1 string)."""
    return [
        {"subject": "dog", "predicate": "eats", "object": "meat"},
        {"subject": "cat", "predicate": "sleeps", "object": "bed"},
        {"subject": "bird", "predicate": "flies", "object": "sky"},
    ]


@pytest.fixture
def sample_llm_responses():
    """Sample LLM responses for synset selection."""
    return [
        TripletWithChosenSynsets(
            subject="dog",
            subject_choices=ElementSynsetChoices(
                element_text="dog",
                chosen_synsets={"dog": "dog.n.01"},
                chosen_hypernyms={"dog": ["dog.n.01", "canine.n.01"]},
            ),
            predicate="eats",
            predicate_choices=ElementSynsetChoices(
                element_text="eats",
                chosen_synsets={"eats": "eat.v.01"},
                chosen_hypernyms={"eats": ["eat.v.01", "consume.v.02"]},
            ),
            object="meat",
            object_choices=ElementSynsetChoices(
                element_text="meat",
                chosen_synsets={"meat": "meat.n.01"},
                chosen_hypernyms={"meat": ["meat.n.01", "food.n.01"]},
            ),
        ),
        TripletWithChosenSynsets(
            subject="cat",
            subject_choices=ElementSynsetChoices(
                element_text="cat",
                chosen_synsets={"cat": "cat.n.01"},
                chosen_hypernyms={"cat": ["cat.n.01", "feline.n.01"]},
            ),
            predicate="sleeps",
            predicate_choices=ElementSynsetChoices(
                element_text="sleeps",
                chosen_synsets={"sleeps": "sleep.v.01"},
                chosen_hypernyms={"sleeps": ["sleep.v.01", "rest.v.01"]},
            ),
            object="bed",
            object_choices=ElementSynsetChoices(
                element_text="bed",
                chosen_synsets={"bed": "bed.n.01"},
                chosen_hypernyms={"bed": ["bed.n.01", "furniture.n.01"]},
            ),
        ),
        TripletWithChosenSynsets(
            subject="bird",
            subject_choices=ElementSynsetChoices(
                element_text="bird",
                chosen_synsets={"bird": "bird.n.01"},
                chosen_hypernyms={"bird": ["bird.n.01", "animal.n.01"]},
            ),
            predicate="flies",
            predicate_choices=ElementSynsetChoices(
                element_text="flies",
                chosen_synsets={"flies": "fly.v.01"},
                chosen_hypernyms={"flies": ["fly.v.01", "move.v.01"]},
            ),
            object="sky",
            object_choices=ElementSynsetChoices(
                element_text="sky",
                chosen_synsets={"sky": "sky.n.01"},
                chosen_hypernyms={"sky": ["sky.n.01", "environment.n.01"]},
            ),
        ),
    ]


class TestBatchAugmentationResult:
    """Test batch augmentation result."""
    
    def test_batch_augmentation_result_creation(self, sample_triplets):
        """Should create valid batch result."""
        augmented = [
            {"subject": {}, "predicate": {}, "object": {}}
            for _ in sample_triplets
        ]
        result = BatchAugmentationResult(triplets=sample_triplets, augmented=augmented)
        
        assert len(result.triplets) == 3
        assert len(result.augmented) == 3
    
    def test_batch_augmentation_to_llm_format(self, orchestrator, sample_triplets):
        """Should format batch for LLM display."""
        batch = orchestrator.augment_batch(sample_triplets)
        
        display = batch.to_llm_format()
        assert isinstance(display, str)
        assert "Triplet" in display or "dog" in display
        assert len(display) > 100


class TestBatchSynsetOrchestrator:
    """Test batch orchestrator."""
    
    def test_augment_batch(self, orchestrator, sample_triplets):
        """Should augment multiple triplets."""
        result = orchestrator.augment_batch(sample_triplets)
        
        assert isinstance(result, BatchAugmentationResult)
        assert len(result.triplets) == 3
        assert len(result.augmented) == 3
    
    def test_augment_batch_preserves_order(self, orchestrator, sample_triplets):
        """Batch augmentation should preserve triplet order."""
        result = orchestrator.augment_batch(sample_triplets)
        
        for orig, aug in zip(result.triplets, result.augmented):
            assert aug["subject"]["element_text"] == orig["subject"]
            assert aug["predicate"]["element_text"] == orig["predicate"]
            assert aug["object"]["element_text"] == orig["object"]
    
    def test_build_batch_selection_prompt(self, orchestrator, sample_triplets):
        """Should build prompt for batch synset selection."""
        batch = orchestrator.augment_batch(sample_triplets)
        prompt = orchestrator.build_batch_selection_prompt(batch)
        
        # Verify it's a string with content from all triplets
        assert isinstance(prompt, str)
        assert len(prompt) > 200  # Non-trivial content
        assert "dog" in prompt
        assert "cat" in prompt
        assert "bird" in prompt
    
    def test_enrich_batch(
        self, orchestrator, sample_triplets, sample_llm_responses
    ):
        """Should enrich multiple triplets with synset choices."""
        batch = orchestrator.augment_batch(sample_triplets)
        result = orchestrator.enrich_batch(batch, sample_llm_responses)
        
        assert isinstance(result, BatchEnrichmentResult)
        assert len(result.enriched_triplets) == 3
        assert len(result.canonical_triplets) == 3
    
    def test_enrich_batch_canonical_triplets(
        self, orchestrator, sample_triplets, sample_llm_responses
    ):
        """Enriched triplets should have canonical forms."""
        batch = orchestrator.augment_batch(sample_triplets)
        result = orchestrator.enrich_batch(batch, sample_llm_responses)
        
        # First canonical triplet
        canonical = result.canonical_triplets[0]
        assert canonical == ("dog.n.01", "eat.v.01", "meat.n.01")
        
        # Second
        canonical = result.canonical_triplets[1]
        assert canonical == ("cat.n.01", "sleep.v.01", "bed.n.01")
    
    def test_enrich_batch_mismatch_error(self, orchestrator, sample_triplets, sample_llm_responses):
        """Should error if response count doesn't match triplet count."""
        batch = orchestrator.augment_batch(sample_triplets)
        
        # Only 2 responses for 3 triplets
        responses = sample_llm_responses[:2]
        
        with pytest.raises(ValueError, match="must match"):
            orchestrator.enrich_batch(batch, responses)
    
    def test_process_batch_end_to_end(
        self, orchestrator, sample_triplets, sample_llm_responses
    ):
        """End-to-end batch processing."""
        result = orchestrator.process_batch(sample_triplets, sample_llm_responses)
        
        assert isinstance(result, BatchEnrichmentResult)
        assert len(result.enriched_triplets) == 3
        
        # Check first enriched triplet
        enriched = result.enriched_triplets[0]
        assert enriched.subject == "dog"
        assert enriched.predicate == "eats"
        assert enriched.object == "meat"


class TestBatchEnrichmentResult:
    """Test batch enrichment results."""
    
    def test_batch_enrichment_to_dict_list(
        self, orchestrator, sample_triplets, sample_llm_responses
    ):
        """Should convert to dict list for storage."""
        batch = orchestrator.augment_batch(sample_triplets)
        result = orchestrator.enrich_batch(batch, sample_llm_responses)
        
        dicts = result.to_dict_list()
        
        assert len(dicts) == 3
        assert all(isinstance(d, dict) for d in dicts)
        
        # First triplet
        assert dicts[0]["subject"] == "dog"
        assert dicts[0]["subject_canonical"] == ("dog.n.01",)


class TestBatchSelectionPromptBuilder:
    """Test batch prompt builder."""
    
    def test_build_prompt_for_batch(
        self, orchestrator, sample_triplets
    ):
        """Should build comprehensive batch prompt."""
        batch = orchestrator.augment_batch(sample_triplets)
        prompt = BatchSelectionPromptBuilder.build_prompt_for_batch(
            sample_triplets, batch
        )
        
        assert isinstance(prompt, str)
        assert "Triplet 1" in prompt
        assert "Triplet 2" in prompt
        assert "Triplet 3" in prompt
        
        # Check for all triplets mentioned
        assert "dog" in prompt
        assert "cat" in prompt
        assert "bird" in prompt
        
        # Check for JSON instruction
        assert "json" in prompt.lower() or "JSON" in prompt
    
    def test_prompt_has_hierarchy_context(self, orchestrator, sample_triplets):
        """Prompt should show hypernym hierarchy."""
        batch = orchestrator.augment_batch(sample_triplets)
        prompt = BatchSelectionPromptBuilder.build_prompt_for_batch(
            sample_triplets, batch
        )
        
        # Should mention arrows for hierarchy
        assert "→" in prompt or "->" in prompt


class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_batch_pipeline(
        self, orchestrator, sample_triplets, sample_llm_responses
    ):
        """Full pipeline: extract → augment → select → enrich."""
        # Simulate extraction: we have 3 triplets from 1 string
        triplets_from_string = sample_triplets
        
        # Augment them
        batch_aug = orchestrator.augment_batch(triplets_from_string)
        assert len(batch_aug.augmented) == 3
        
        # Build prompt for LLM
        prompt = orchestrator.build_batch_selection_prompt(batch_aug)
        assert len(prompt) > 100
        
        # Simulate LLM response (we have them)
        llm_responses = sample_llm_responses
        
        # Enrich
        batch_enriched = orchestrator.enrich_batch(batch_aug, llm_responses)
        assert len(batch_enriched.enriched_triplets) == 3
        
        # Get canonical triplets ready for graph
        canonicals = batch_enriched.canonical_triplets
        assert all(len(c) == 3 for c in canonicals)  # All are (subj, pred, obj)
    
    def test_batch_vs_individual_consistency(
        self, orchestrator, sample_triplets, sample_llm_responses
    ):
        """Batch processing should give same results as individual."""
        from triplet_enrichment import TripletEnricher
        
        # Individual processing
        individual_canonicals = []
        for triplet, response in zip(sample_triplets, sample_llm_responses):
            enriched = TripletEnricher.enrich_from_llm_response(triplet, response)
            from triplet_enrichment import CanonicalityRules
            canonical = CanonicalityRules.canonical_triplet(enriched)
            individual_canonicals.append(canonical)
        
        # Batch processing
        batch_result = orchestrator.process_batch(
            sample_triplets, sample_llm_responses
        )
        batch_canonicals = batch_result.canonical_triplets
        
        # Should be identical
        assert individual_canonicals == batch_canonicals


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
