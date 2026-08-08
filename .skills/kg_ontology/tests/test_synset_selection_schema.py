"""
Unit tests for synset selection schema and prompt builder.

Tests:
- TripletWithChosenSynsets schema validation
- SynsetSelectionPromptBuilder formatting
- Prompt generation for LLM input
"""

import pytest
import sys
import os
from typing import Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synset_selection_schema import (
    ElementSynsetChoices,
    TripletWithChosenSynsets,
    SynsetSelectionPromptBuilder,
)
from synset_augmentation import TripletsToAugmentedCandidates


@pytest.fixture
def orchestrator():
    """Initialize orchestrator without word2vec (NLTK only)."""
    return TripletsToAugmentedCandidates(word2vec_model=None, use_nltk_stopwords=True, k_neighbors=5)


@pytest.fixture
def sample_triplet():
    """Sample extracted triplet."""
    return {
        "subject": "dog",
        "predicate": "eats",
        "object": "meat",
    }


@pytest.fixture
def augmented_candidates(orchestrator, sample_triplet):
    """Augmented candidates for sample triplet."""
    return orchestrator.augment_triplet(sample_triplet)


class TestElementSynsetChoices:
    """Test ElementSynsetChoices schema."""
    
    def test_element_synset_choices_creation(self):
        """Should create valid ElementSynsetChoices."""
        choices = ElementSynsetChoices(
            element_text="dog",
            chosen_synsets={"dog": "dog.n.01"},
            chosen_hypernyms={"dog": ["dog.n.01", "canine.n.01"]},
        )
        assert choices.element_text == "dog"
        assert choices.chosen_synsets == {"dog": "dog.n.01"}
        assert choices.chosen_hypernyms == {"dog": ["dog.n.01", "canine.n.01"]}
    
    def test_element_synset_choices_multiword(self):
        """Should handle multi-word elements."""
        choices = ElementSynsetChoices(
            element_text="quick brown dog",
            chosen_synsets={"quick": "quick.a.01", "brown": "brown.a.01", "dog": "dog.n.01"},
            chosen_hypernyms={
                "quick": ["quick.a.01", "adjective.a.01"],
                "brown": ["brown.a.01", "adjective.a.01"],
                "dog": ["dog.n.01", "canine.n.01"],
            },
        )
        assert len(choices.chosen_synsets) == 3
        assert len(choices.chosen_hypernyms) == 3


class TestTripletWithChosenSynsets:
    """Test TripletWithChosenSynsets schema."""
    
    def test_triplet_with_chosen_synsets_creation(self):
        """Should create valid triplet with synsets."""
        triplet = TripletWithChosenSynsets(
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
            polarity="affirmed",
            inference_type="observed",
        )
        
        assert triplet.subject == "dog"
        assert triplet.predicate == "eats"
        assert triplet.object == "meat"
        assert triplet.polarity == "affirmed"
        assert triplet.inference_type == "observed"
    
    def test_triplet_with_chosen_synsets_polarity_negated(self):
        """Should accept negated polarity."""
        triplet = TripletWithChosenSynsets(
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
            polarity="negated",
            inference_type="inferred",
        )
        
        assert triplet.polarity == "negated"
        assert triplet.inference_type == "inferred"
    
    def test_to_canonical_triplet(self):
        """Should convert to canonical triplet format."""
        triplet = TripletWithChosenSynsets(
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
        )
        
        canonical = triplet.to_canonical_triplet()
        
        assert canonical["subject"] == "dog"
        assert canonical["subject_synsets"] == ["dog.n.01"]
        assert canonical["subject_hypernyms"] == [["dog.n.01", "canine.n.01"]]
        
        assert canonical["predicate"] == "eats"
        assert canonical["predicate_synsets"] == ["eat.v.01"]
        
        assert canonical["object"] == "meat"
        assert canonical["object_synsets"] == ["meat.n.01"]
        
        assert canonical["polarity"] == "affirmed"
        assert canonical["inference_type"] == "observed"
    
    def test_to_canonical_triplet_multiword_subject(self):
        """Should handle multi-word elements in canonical format."""
        triplet = TripletWithChosenSynsets(
            subject="quick brown dog",
            subject_choices=ElementSynsetChoices(
                element_text="quick brown dog",
                chosen_synsets={"quick": "quick.a.01", "brown": "brown.a.01", "dog": "dog.n.01"},
                chosen_hypernyms={
                    "quick": ["quick.a.01", "adj.a.01"],
                    "brown": ["brown.a.01", "adj.a.01"],
                    "dog": ["dog.n.01", "canine.n.01"],
                },
            ),
            predicate="runs",
            predicate_choices=ElementSynsetChoices(
                element_text="runs",
                chosen_synsets={"runs": "run.v.01"},
                chosen_hypernyms={"runs": ["run.v.01", "move.v.01"]},
            ),
            object="park",
            object_choices=ElementSynsetChoices(
                element_text="park",
                chosen_synsets={"park": "park.n.01"},
                chosen_hypernyms={"park": ["park.n.01", "area.n.01"]},
            ),
        )
        
        canonical = triplet.to_canonical_triplet()
        
        # Multi-word subject should have all synsets
        assert len(canonical["subject_synsets"]) == 3
        assert "quick.a.01" in canonical["subject_synsets"]
        assert "dog.n.01" in canonical["subject_synsets"]


class TestSynsetSelectionPromptBuilder:
    """Test prompt builder for synset selection."""
    
    def test_format_candidates_for_element(self, augmented_candidates):
        """Should format element candidates as readable text."""
        subject_aug = augmented_candidates["subject"]
        formatted = SynsetSelectionPromptBuilder.format_candidates_for_element(subject_aug)
        
        assert isinstance(formatted, str)
        assert "dog" in formatted
        assert "synset" in formatted or "dog.n.01" in formatted
    
    def test_build_synset_selection_prompt_structure(self, sample_triplet, augmented_candidates):
        """Prompt should have correct structure."""
        prompt = SynsetSelectionPromptBuilder.build_synset_selection_prompt(
            sample_triplet, augmented_candidates
        )
        
        assert isinstance(prompt, str)
        
        # Check for key sections
        assert "subject" in prompt.lower()
        assert "predicate" in prompt.lower()
        assert "object" in prompt.lower()
        
        # Check for JSON instruction
        assert "json" in prompt.lower()
        assert "chosen_synsets" in prompt
        assert "chosen_hypernyms" in prompt
    
    def test_build_synset_selection_prompt_contains_original_phrases(self, sample_triplet, augmented_candidates):
        """Prompt should include original extracted phrases."""
        prompt = SynsetSelectionPromptBuilder.build_synset_selection_prompt(
            sample_triplet, augmented_candidates
        )
        
        assert "dog" in prompt
        assert "eats" in prompt
        assert "meat" in prompt
    
    def test_build_synset_selection_prompt_has_candidates(self, sample_triplet, augmented_candidates):
        """Prompt should include synset options."""
        prompt = SynsetSelectionPromptBuilder.build_synset_selection_prompt(
            sample_triplet, augmented_candidates
        )
        
        # Should mention synsets/options
        assert "dog.n.01" in prompt or "canine" in prompt or "options" in prompt


class TestPromptFormatting:
    """Test prompt formatting edge cases."""
    
    def test_prompt_with_multiword_subject(self, orchestrator):
        """Prompt should handle multi-word subjects."""
        triplet = {
            "subject": "quick brown dog",
            "predicate": "runs",
            "object": "park",
        }
        augmented = orchestrator.augment_triplet(triplet)
        
        prompt = SynsetSelectionPromptBuilder.build_synset_selection_prompt(triplet, augmented)
        
        assert "quick brown dog" in prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Prompt should be substantial
    
    def test_prompt_json_response_format(self, sample_triplet, augmented_candidates):
        """Prompt should specify exact JSON format."""
        prompt = SynsetSelectionPromptBuilder.build_synset_selection_prompt(
            sample_triplet, augmented_candidates
        )
        
        # Should show JSON structure
        assert "{" in prompt
        assert "}" in prompt
        assert ":" in prompt


class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_prompt_generation_and_schema(self, orchestrator):
        """Full pipeline: extract → augment → prompt → schema."""
        triplet = {
            "subject": "dog",
            "predicate": "eats",
            "object": "meat",
        }
        
        # Augment
        augmented = orchestrator.augment_triplet(triplet)
        
        # Build prompt
        prompt = SynsetSelectionPromptBuilder.build_synset_selection_prompt(triplet, augmented)
        
        # Schema should be valid
        example_response = TripletWithChosenSynsets(
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
        )
        
        assert example_response is not None
        assert isinstance(prompt, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
