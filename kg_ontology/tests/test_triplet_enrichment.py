"""
Unit tests for triplet enrichment and canonicalization.

Tests:
- EnrichedTriplet creation and validation
- Canonical identity generation
- BM25 text enrichment
- Backward compatibility migration
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triplet_enrichment import (
    EnrichedTriplet,
    TripletEnricher,
    CanonicalityRules,
    BackwardCompatibilityMigrator,
)
from synset_selection_schema import (
    ElementSynsetChoices,
    TripletWithChosenSynsets,
)


@pytest.fixture
def sample_triplet_with_synsets():
    """Sample LLM response with chosen synsets."""
    return TripletWithChosenSynsets(
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


class TestEnrichedTriplet:
    """Test EnrichedTriplet creation and validation."""
    
    def test_enriched_triplet_creation(self):
        """Should create valid enriched triplet."""
        enriched = EnrichedTriplet(
            subject="dog",
            subject_synsets={"dog": "dog.n.01"},
            subject_hypernyms={"dog": ["dog.n.01", "canine.n.01"]},
            predicate="eats",
            predicate_synsets={"eats": "eat.v.01"},
            predicate_hypernyms={"eats": ["eat.v.01", "consume.v.02"]},
            object="meat",
            object_synsets={"meat": "meat.n.01"},
            object_hypernyms={"meat": ["meat.n.01", "food.n.01"]},
        )
        
        assert enriched.subject == "dog"
        assert enriched.predicate == "eats"
        assert enriched.object == "meat"
    
    def test_enriched_triplet_computes_canonical(self):
        """Should compute canonical identities after initialization."""
        enriched = EnrichedTriplet(
            subject="dog",
            subject_synsets={"dog": "dog.n.01"},
            subject_hypernyms={"dog": ["dog.n.01", "canine.n.01"]},
            predicate="eats",
            predicate_synsets={"eats": "eat.v.01"},
            predicate_hypernyms={"eats": ["eat.v.01", "consume.v.02"]},
            object="meat",
            object_synsets={"meat": "meat.n.01"},
            object_hypernyms={"meat": ["meat.n.01", "food.n.01"]},
        )
        
        # Canonical should be computed
        assert enriched.subject_canonical == ("dog.n.01",)
        assert enriched.predicate_canonical == ("eat.v.01",)
        assert enriched.object_canonical == ("meat.n.01",)
    
    def test_enriched_triplet_computes_bm25_text(self):
        """Should compute BM25 enrichment text."""
        enriched = EnrichedTriplet(
            subject="dog",
            subject_synsets={"dog": "dog.n.01"},
            subject_hypernyms={"dog": ["dog.n.01", "canine.n.01"]},
            predicate="eats",
            predicate_synsets={"eats": "eat.v.01"},
            predicate_hypernyms={"eats": ["eat.v.01", "consume.v.02"]},
            object="meat",
            object_synsets={"meat": "meat.n.01"},
            object_hypernyms={"meat": ["meat.n.01", "food.n.01"]},
        )
        
        # BM25 text should include synsets + hypernyms
        assert "dog.n.01" in enriched.bm25_subject
        assert "canine.n.01" in enriched.bm25_subject
    
    def test_enriched_triplet_multiword_subject(self):
        """Should handle multi-word elements."""
        enriched = EnrichedTriplet(
            subject="quick brown dog",
            subject_synsets={
                "quick": "quick.a.01",
                "brown": "brown.a.01",
                "dog": "dog.n.01",
            },
            subject_hypernyms={
                "quick": ["quick.a.01", "adj.a.01"],
                "brown": ["brown.a.01", "adj.a.01"],
                "dog": ["dog.n.01", "canine.n.01"],
            },
            predicate="runs",
            predicate_synsets={"runs": "run.v.01"},
            predicate_hypernyms={"runs": ["run.v.01", "move.v.01"]},
            object="park",
            object_synsets={"park": "park.n.01"},
            object_hypernyms={"park": ["park.n.01", "area.n.01"]},
        )
        
        # Canonical should have all three synsets (sorted)
        assert len(enriched.subject_canonical) == 3
        assert "dog.n.01" in enriched.subject_canonical
        assert "quick.a.01" in enriched.subject_canonical
    
    def test_enriched_triplet_to_dict(self):
        """Should convert to dict."""
        enriched = EnrichedTriplet(
            subject="dog",
            subject_synsets={"dog": "dog.n.01"},
            subject_hypernyms={"dog": ["dog.n.01", "canine.n.01"]},
            predicate="eats",
            predicate_synsets={"eats": "eat.v.01"},
            predicate_hypernyms={"eats": ["eat.v.01", "consume.v.02"]},
            object="meat",
            object_synsets={"meat": "meat.n.01"},
            object_hypernyms={"meat": ["meat.n.01", "food.n.01"]},
        )
        
        d = enriched.to_dict()
        assert isinstance(d, dict)
        assert d["subject"] == "dog"
        assert d["subject_canonical"] == ("dog.n.01",)


class TestTripletEnricher:
    """Test enrichment from LLM response."""
    
    def test_enrich_from_llm_response(self, sample_triplet_with_synsets):
        """Should merge extracted triplet with LLM choices."""
        extracted = {
            "subject": "dog",
            "predicate": "eats",
            "object": "meat",
        }
        
        enriched = TripletEnricher.enrich_from_llm_response(extracted, sample_triplet_with_synsets)
        
        assert isinstance(enriched, EnrichedTriplet)
        assert enriched.subject == "dog"
        assert enriched.subject_synsets == {"dog": "dog.n.01"}
        assert enriched.subject_hypernyms == {"dog": ["dog.n.01", "canine.n.01"]}
    
    def test_validate_enrichment_valid(self, sample_triplet_with_synsets):
        """Valid enrichment should pass validation."""
        enriched = TripletEnricher.enrich_from_llm_response(
            {"subject": "dog", "predicate": "eats", "object": "meat"},
            sample_triplet_with_synsets,
        )
        
        errors = TripletEnricher.validate_enrichment(enriched)
        assert len(errors) == 0
    
    def test_validate_enrichment_missing_hypernym(self):
        """Missing hypernym entry should fail validation."""
        enriched = EnrichedTriplet(
            subject="dog",
            subject_synsets={"dog": "dog.n.01", "brown": "brown.a.01"},  # 2 words
            subject_hypernyms={"dog": ["dog.n.01", "canine.n.01"]},  # Only 1 word
            predicate="eats",
            predicate_synsets={"eats": "eat.v.01"},
            predicate_hypernyms={"eats": ["eat.v.01", "consume.v.02"]},
            object="meat",
            object_synsets={"meat": "meat.n.01"},
            object_hypernyms={"meat": ["meat.n.01", "food.n.01"]},
        )
        
        errors = TripletEnricher.validate_enrichment(enriched)
        assert len(errors) > 0
        assert any("brown" in err for err in errors)


class TestCanonicalityRules:
    """Test canonical identity generation."""
    
    def test_canonical_node_id_single_word(self):
        """Single synset should return as-is."""
        node_id = CanonicalityRules.canonical_node_id(("dog.n.01",))
        assert node_id == "dog.n.01"
    
    def test_canonical_node_id_multiword(self):
        """Multi-word should be joined with +."""
        node_id = CanonicalityRules.canonical_node_id(("quick.a.01", "dog.n.01", "brown.a.01"))
        # Should be sorted
        assert "brown.a.01" in node_id
        assert "dog.n.01" in node_id
        assert "quick.a.01" in node_id
        assert "+" in node_id
    
    def test_subject_canonical_id(self, sample_triplet_with_synsets):
        """Should get subject canonical ID."""
        enriched = TripletEnricher.enrich_from_llm_response(
            {"subject": "dog", "predicate": "eats", "object": "meat"},
            sample_triplet_with_synsets,
        )
        
        subject_id = CanonicalityRules.subject_canonical_id(enriched)
        assert subject_id == "dog.n.01"
    
    def test_predicate_canonical_id(self, sample_triplet_with_synsets):
        """Should get predicate canonical ID."""
        enriched = TripletEnricher.enrich_from_llm_response(
            {"subject": "dog", "predicate": "eats", "object": "meat"},
            sample_triplet_with_synsets,
        )
        
        pred_id = CanonicalityRules.predicate_canonical_id(enriched)
        assert pred_id == "eat.v.01"
    
    def test_object_canonical_id(self, sample_triplet_with_synsets):
        """Should get object canonical ID."""
        enriched = TripletEnricher.enrich_from_llm_response(
            {"subject": "dog", "predicate": "eats", "object": "meat"},
            sample_triplet_with_synsets,
        )
        
        obj_id = CanonicalityRules.object_canonical_id(enriched)
        assert obj_id == "meat.n.01"
    
    def test_canonical_triplet(self, sample_triplet_with_synsets):
        """Should generate canonical triplet tuple."""
        enriched = TripletEnricher.enrich_from_llm_response(
            {"subject": "dog", "predicate": "eats", "object": "meat"},
            sample_triplet_with_synsets,
        )
        
        triplet = CanonicalityRules.canonical_triplet(enriched)
        assert triplet == ("dog.n.01", "eat.v.01", "meat.n.01")


class TestBackwardCompatibilityMigrator:
    """Test schema migration for legacy triplets."""
    
    def test_migrate_legacy_triplet(self):
        """Should add synset columns as NULL."""
        legacy = {
            "subject": "dog",
            "predicate": "eats",
            "object": "meat",
        }
        
        migrated = BackwardCompatibilityMigrator.migrate_legacy_triplet(legacy)
        
        # Original fields preserved
        assert migrated["subject"] == "dog"
        assert migrated["predicate"] == "eats"
        assert migrated["object"] == "meat"
        
        # New fields added as NULL
        assert migrated["subject_synsets"] is None
        assert migrated["subject_hypernyms"] is None
        assert migrated["predicate_synsets"] is None
        assert migrated["object_synsets"] is None
        
        # Provenance marked
        assert migrated["migration_provenance"] == "pre_synset_extraction"
    
    def test_migrate_legacy_preserves_existing_fields(self):
        """Should preserve polarity and inference_type if present."""
        legacy = {
            "subject": "dog",
            "predicate": "eats",
            "object": "meat",
            "polarity": "negated",
            "inference_type": "inferred",
        }
        
        migrated = BackwardCompatibilityMigrator.migrate_legacy_triplet(legacy)
        
        assert migrated["polarity"] == "negated"
        assert migrated["inference_type"] == "inferred"


class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_enrichment_pipeline(self, sample_triplet_with_synsets):
        """Full pipeline: LLM response → enriched triplet → canonical IDs."""
        extracted = {"subject": "dog", "predicate": "eats", "object": "meat"}
        
        # Enrich
        enriched = TripletEnricher.enrich_from_llm_response(extracted, sample_triplet_with_synsets)
        
        # Validate
        errors = TripletEnricher.validate_enrichment(enriched)
        assert len(errors) == 0
        
        # Get canonical IDs
        canonical = CanonicalityRules.canonical_triplet(enriched)
        assert canonical == ("dog.n.01", "eat.v.01", "meat.n.01")
        
        # Should be ready for storage
        d = enriched.to_dict()
        assert d is not None
        assert len(d) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
