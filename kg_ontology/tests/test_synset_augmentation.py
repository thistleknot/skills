"""
Unit tests for synset augmentation orchestrator.

Tests the pipeline:
- Split element into content words
- Retrieve word2vec neighbors (if model available)
- Lookup synsets + hypernyms
- Build hierarchical candidate display
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synset_augmentation import (
    TripletsToAugmentedCandidates,
    SynsetCandidate,
    WordWithCandidates,
    ElementAugmentation,
)


@pytest.fixture
def orchestrator():
    """Initialize orchestrator without word2vec (NLTK only)."""
    return TripletsToAugmentedCandidates(word2vec_model=None, use_nltk_stopwords=True, k_neighbors=5)


class TestStopWordFiltering:
    """Test stop word filtering and tokenization."""
    
    def test_split_element_filters_stopwords(self, orchestrator):
        """Content words should exclude stop words."""
        result = orchestrator.split_element_into_words("the quick brown dog")
        assert "the" not in result  # Stopword
        assert "quick" in result
        assert "brown" in result
        assert "dog" in result
    
    def test_split_element_strips_punctuation(self, orchestrator):
        """Punctuation should be stripped."""
        result = orchestrator.split_element_into_words("the dog.")
        assert "dog" in result
        assert "dog." not in result
    
    def test_split_element_lowercase(self, orchestrator):
        """Result should be lowercase."""
        result = orchestrator.split_element_into_words("The DOG")
        assert all(word.islower() for word in result)
    
    def test_split_element_single_word(self, orchestrator):
        """Single content word should be extracted."""
        result = orchestrator.split_element_into_words("dog")
        assert result == ["dog"]
    
    def test_split_element_all_stopwords(self, orchestrator):
        """Elements with only stop words should return empty list."""
        result = orchestrator.split_element_into_words("the a an")
        assert result == []


class TestSynsetLookup:
    """Test synset lookup via NLTK."""
    
    def test_get_synset_for_common_word(self, orchestrator):
        """Common words should have synsets."""
        synset = orchestrator.get_synset_for_word("dog")
        assert synset is not None
        assert "dog" in synset
        assert ".n." in synset  # Noun
    
    def test_get_synset_returns_first_sense(self, orchestrator):
        """Should return most common sense."""
        synset = orchestrator.get_synset_for_word("dog")
        # "dog.n.01" is typically the most common sense
        assert synset == "dog.n.01"
    
    def test_get_synset_for_unknown_word(self, orchestrator):
        """Unknown word should return None."""
        synset = orchestrator.get_synset_for_word("xyzabc123notaword")
        assert synset is None
    
    def test_get_synset_caching(self, orchestrator):
        """Synset lookups should be cached."""
        s1 = orchestrator.get_synset_for_word("dog")
        s2 = orchestrator.get_synset_for_word("dog")
        assert s1 == s2
        # Same object due to caching
        assert orchestrator.get_synset_for_word.cache_info().hits >= 1


class TestHypernymLookup:
    """Test hypernym lookup via NLTK."""
    
    def test_get_hypernym_for_synset(self, orchestrator):
        """Common synsets should have hypernyms."""
        hyp = orchestrator.get_hypernym("dog.n.01")
        assert hyp is not None
        hyp_id, hyp_label = hyp
        # WordNet hierarchy: dog.n.01 → domestic_animal.n.01 or canine.n.01
        assert isinstance(hyp_id, str) and isinstance(hyp_label, str)
    
    def test_get_hypernym_returns_tuple(self, orchestrator):
        """Should return (synset_id, label) tuple."""
        hyp = orchestrator.get_hypernym("dog.n.01")
        assert isinstance(hyp, tuple)
        assert len(hyp) == 2
        assert isinstance(hyp[0], str)  # synset_id
        assert isinstance(hyp[1], str)  # label
    
    def test_get_hypernym_for_root_synset(self, orchestrator):
        """Root synsets may have no hypernyms."""
        # "entity.n.01" is near the root
        hyp = orchestrator.get_hypernym("entity.n.01")
        # May or may not have hypernym depending on hierarchy
        assert hyp is None or isinstance(hyp, tuple)


class TestCandidateGeneration:
    """Test building candidate lists for words."""
    
    def test_get_synset_candidates_for_word(self, orchestrator):
        """Should return candidates for a word."""
        candidates = orchestrator.get_synset_candidates_for_word("dog")
        assert len(candidates) > 0
        assert all(isinstance(c, SynsetCandidate) for c in candidates)
    
    def test_first_candidate_is_word_itself(self, orchestrator):
        """First candidate should typically be the word itself."""
        candidates = orchestrator.get_synset_candidates_for_word("dog")
        assert candidates[0].word == "dog"
        assert candidates[0].synset_id == "dog.n.01"
    
    def test_candidates_have_hypernyms(self, orchestrator):
        """Candidates should include hypernym context."""
        candidates = orchestrator.get_synset_candidates_for_word("dog")
        for candidate in candidates:
            if candidate.hypernym_id:
                assert candidate.hypernym_label is not None
    
    def test_candidates_limited_to_k(self, orchestrator):
        """Candidates should not exceed k_neighbors."""
        candidates = orchestrator.get_synset_candidates_for_word("dog")
        assert len(candidates) <= orchestrator.k_neighbors
    
    def test_candidate_to_dict_format(self, orchestrator):
        """Candidates should format to dict for LLM display."""
        candidates = orchestrator.get_synset_candidates_for_word("dog")
        for candidate in candidates:
            d = candidate.to_dict()
            assert "word" in d
            assert "synset" in d
            assert "hypernym_chain" in d
            assert "pos" in d


class TestElementAugmentation:
    """Test augmenting single elements."""
    
    def test_augment_element_single_word(self, orchestrator):
        """Single-word element should produce one WordWithCandidates."""
        result = orchestrator.augment_element("dog")
        assert isinstance(result, ElementAugmentation)
        assert result.element_text == "dog"
        assert len(result.content_words) == 1
        assert len(result.words_with_candidates) == 1
    
    def test_augment_element_multiword(self, orchestrator):
        """Multi-word element should produce candidates per content word."""
        result = orchestrator.augment_element("quick brown dog")
        assert isinstance(result, ElementAugmentation)
        # "quick", "brown", "dog" (excluding stopwords)
        assert len(result.content_words) == 3
        assert len(result.words_with_candidates) == 3
    
    def test_augment_element_to_dict(self, orchestrator):
        """ElementAugmentation should format to dict."""
        result = orchestrator.augment_element("dog")
        d = result.to_dict()
        assert "element_text" in d
        assert "word_options" in d
        assert isinstance(d["word_options"], list)


class TestTripletAugmentation:
    """Test augmenting complete triplets."""
    
    def test_augment_triplet(self, orchestrator):
        """Triplet augmentation should produce results for all three elements."""
        triplet = {
            "subject": "dog",
            "predicate": "eats",
            "object": "meat",
        }
        result = orchestrator.augment_triplet(triplet)
        
        assert "subject" in result
        assert "predicate" in result
        assert "object" in result
        
        assert all(isinstance(v, ElementAugmentation) for v in result.values())
    
    def test_triplet_to_display_format(self, orchestrator):
        """Triplet should format to display dict for LLM."""
        triplet = {
            "subject": "dog",
            "predicate": "eats",
            "object": "meat",
        }
        result = orchestrator.triplet_to_display_format(triplet)
        
        assert "subject" in result
        assert "predicate" in result
        assert "object" in result
        
        # Each should have word_options
        for key in ["subject", "predicate", "object"]:
            assert "word_options" in result[key]


class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_pipeline_dog_eats_meat(self, orchestrator):
        """End-to-end: "dog eats meat" triplet."""
        triplet = {
            "subject": "dog",
            "predicate": "eats",
            "object": "meat",
        }
        
        display_format = orchestrator.triplet_to_display_format(triplet)
        
        # Verify structure
        assert display_format["subject"]["element_text"] == "dog"
        assert display_format["predicate"]["element_text"] == "eats"
        assert display_format["object"]["element_text"] == "meat"
        
        # Verify candidates exist
        for key in ["subject", "predicate", "object"]:
            word_options = display_format[key]["word_options"]
            assert len(word_options) > 0
            for word_opt in word_options:
                assert "word" in word_opt
                assert "synset_options" in word_opt
                assert len(word_opt["synset_options"]) > 0
    
    def test_full_pipeline_multiword_subject(self, orchestrator):
        """End-to-end: multi-word subject."""
        triplet = {
            "subject": "quick brown dog",
            "predicate": "runs",
            "object": "park",
        }
        
        display_format = orchestrator.triplet_to_display_format(triplet)
        
        subject_words = display_format["subject"]["word_options"]
        # Should have candidates for "quick", "brown", "dog"
        assert len(subject_words) >= 2  # At least brown and dog (quick might have no synsets)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
