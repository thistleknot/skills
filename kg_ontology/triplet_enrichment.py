"""
Phase 3: Triplet enrichment and kg_ontology integration.

After LLM selects synsets, this module:
1. Merges extracted triplets with chosen synsets + hypernyms
2. Computes canonical identities (synset tuples)
3. Injects hypernyms into BM25 text for vertical alignment
4. Handles schema updates for triplet storage
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json

try:
    from .synset_selection_schema import TripletWithChosenSynsets, ElementSynsetChoices
except ImportError:  # pragma: no cover - fallback for direct module execution
    from synset_selection_schema import TripletWithChosenSynsets, ElementSynsetChoices


@dataclass
class EnrichedTriplet:
    """
    Complete enriched triplet with all metadata.
    
    After LLM selects synsets, this represents the full triplet ready for storage.
    """
    
    # Surface forms
    subject: str
    predicate: str
    object: str
    
    # Synsets per word
    subject_synsets: Dict[str, str]  # word → synset_id
    subject_hypernyms: Dict[str, List[str]]  # word → [current_synset, hypernym]
    predicate_synsets: Dict[str, str]
    predicate_hypernyms: Dict[str, List[str]]
    object_synsets: Dict[str, str]
    object_hypernyms: Dict[str, List[str]]
    
    # Canonical identities (tuples of synsets)
    subject_canonical: Tuple[str, ...] = None  # Tuple of all synsets for subject
    predicate_canonical: Tuple[str, ...] = None
    object_canonical: Tuple[str, ...] = None
    
    # Metadata
    polarity: str = "affirmed"
    inference_type: str = "observed"
    confidence: float = 1.0
    
    # For BM25 enrichment
    bm25_subject: str = ""  # Subject synsets + hypernyms joined
    bm25_predicate: str = ""
    bm25_object: str = ""
    
    def __post_init__(self):
        """Compute canonical identities and BM25 text if not provided."""
        if self.subject_canonical is None:
            self.subject_canonical = tuple(sorted(self.subject_synsets.values()))
        if self.predicate_canonical is None:
            self.predicate_canonical = tuple(sorted(self.predicate_synsets.values()))
        if self.object_canonical is None:
            self.object_canonical = tuple(sorted(self.object_synsets.values()))
        
        # Compute BM25 enrichment
        if not self.bm25_subject:
            self.bm25_subject = self._compute_bm25_text(self.subject_hypernyms)
        if not self.bm25_predicate:
            self.bm25_predicate = self._compute_bm25_text(self.predicate_hypernyms)
        if not self.bm25_object:
            self.bm25_object = self._compute_bm25_text(self.object_hypernyms)
    
    @staticmethod
    def _compute_bm25_text(hypernyms_dict: Dict[str, List[str]]) -> str:
        """
        Build BM25 text for vertical alignment.
        
        Concatenates all synsets + hypernyms for a single element.
        Example: {"dog": ["dog.n.01", "canine.n.01"]} → "dog.n.01 canine.n.01"
        
        Args:
            hypernyms_dict: Dict mapping word → [current_synset, hypernym_id]
        
        Returns:
            Space-separated synset IDs for BM25 indexing
        """
        all_synsets = []
        for word, chain in hypernyms_dict.items():
            all_synsets.extend(chain)
        return " ".join(all_synsets)
    
    def to_dict(self) -> Dict:
        """Convert to dict for storage/serialization."""
        return {
            "subject": self.subject,
            "subject_synsets": self.subject_synsets,
            "subject_hypernyms": self.subject_hypernyms,
            "subject_canonical": self.subject_canonical,
            "bm25_subject": self.bm25_subject,
            
            "predicate": self.predicate,
            "predicate_synsets": self.predicate_synsets,
            "predicate_hypernyms": self.predicate_hypernyms,
            "predicate_canonical": self.predicate_canonical,
            "bm25_predicate": self.bm25_predicate,
            
            "object": self.object,
            "object_synsets": self.object_synsets,
            "object_hypernyms": self.object_hypernyms,
            "object_canonical": self.object_canonical,
            "bm25_object": self.bm25_object,
            
            "polarity": self.polarity,
            "inference_type": self.inference_type,
            "confidence": self.confidence,
        }


class TripletEnricher:
    """
    Enriches extracted triplets with chosen synsets.
    
    Combines:
    - Extracted triplet (surface forms)
    - LLM's chosen synsets (TripletWithChosenSynsets)
    
    Into:
    - EnrichedTriplet with canonical identities + BM25 enrichment
    """
    
    @staticmethod
    def enrich_from_llm_response(
        extracted_triplet: Dict[str, str],
        llm_synset_response: TripletWithChosenSynsets,
    ) -> EnrichedTriplet:
        """
        Merge extracted triplet with LLM's synset choices.
        
        Args:
            extracted_triplet: {"subject": "...", "predicate": "...", "object": "..."}
            llm_synset_response: TripletWithChosenSynsets with chosen synsets
        
        Returns:
            EnrichedTriplet with all metadata
        """
        return EnrichedTriplet(
            subject=llm_synset_response.subject,
            subject_synsets=llm_synset_response.subject_choices.chosen_synsets,
            subject_hypernyms=llm_synset_response.subject_choices.chosen_hypernyms,
            
            predicate=llm_synset_response.predicate,
            predicate_synsets=llm_synset_response.predicate_choices.chosen_synsets,
            predicate_hypernyms=llm_synset_response.predicate_choices.chosen_hypernyms,
            
            object=llm_synset_response.object,
            object_synsets=llm_synset_response.object_choices.chosen_synsets,
            object_hypernyms=llm_synset_response.object_choices.chosen_hypernyms,
            
            polarity=llm_synset_response.polarity,
            inference_type=llm_synset_response.inference_type,
        )
    
    @staticmethod
    def validate_enrichment(enriched: EnrichedTriplet) -> List[str]:
        """
        Validate enriched triplet for consistency.
        
        Checks:
        - All words in chosen_synsets have corresponding hypernym entries
        - No empty canonical identities
        - BM25 text is non-empty
        
        Args:
            enriched: EnrichedTriplet to validate
        
        Returns:
            List of validation errors (empty list = valid)
        """
        errors = []
        
        # Check subject
        for word in enriched.subject_synsets:
            if word not in enriched.subject_hypernyms:
                errors.append(f"Subject word '{word}' has no hypernym entry")
        
        # Check predicate
        for word in enriched.predicate_synsets:
            if word not in enriched.predicate_hypernyms:
                errors.append(f"Predicate word '{word}' has no hypernym entry")
        
        # Check object
        for word in enriched.object_synsets:
            if word not in enriched.object_hypernyms:
                errors.append(f"Object word '{word}' has no hypernym entry")
        
        # Check canonical identities
        if not enriched.subject_canonical:
            errors.append("Subject has empty canonical identity")
        if not enriched.predicate_canonical:
            errors.append("Predicate has empty canonical identity")
        if not enriched.object_canonical:
            errors.append("Object has empty canonical identity")
        
        return errors


class CanonicalityRules:
    """
    Rules for mapping enriched triplets to canonical forms.
    
    Canonical form usage:
    - Graph node IDs: use canonical tuples
    - Aliases: map surface forms to canonical IDs
    - Vertical alignment: use BM25 text for retrieval
    """
    
    @staticmethod
    def canonical_node_id(synset_tuple: Tuple[str, ...], element_type: str = "entity") -> str:
        """
        Generate canonical node ID from synset tuple.
        
        For single-word element: "dog.n.01"
        For multi-word element: "dog.n.01+food.n.01" (sorted, joined by +)
        
        Args:
            synset_tuple: Tuple of synset IDs
            element_type: "entity", "predicate", etc. (for debugging)
        
        Returns:
            Canonical node ID string
        """
        if not synset_tuple:
            return f"{element_type}:unknown"
        
        if len(synset_tuple) == 1:
            return synset_tuple[0]
        else:
            return "+".join(sorted(synset_tuple))
    
    @staticmethod
    def subject_canonical_id(enriched: EnrichedTriplet) -> str:
        """Canonical ID for subject (entity)."""
        return CanonicalityRules.canonical_node_id(enriched.subject_canonical, "entity")
    
    @staticmethod
    def predicate_canonical_id(enriched: EnrichedTriplet) -> str:
        """Canonical ID for predicate (relation)."""
        return CanonicalityRules.canonical_node_id(enriched.predicate_canonical, "relation")
    
    @staticmethod
    def object_canonical_id(enriched: EnrichedTriplet) -> str:
        """Canonical ID for object (entity or value)."""
        return CanonicalityRules.canonical_node_id(enriched.object_canonical, "entity")
    
    @staticmethod
    def canonical_triplet(enriched: EnrichedTriplet) -> Tuple[str, str, str]:
        """
        Generate canonical triplet tuple: (subject_id, predicate_id, object_id).
        
        This is the triple used as the node identity in the knowledge graph.
        """
        return (
            CanonicalityRules.subject_canonical_id(enriched),
            CanonicalityRules.predicate_canonical_id(enriched),
            CanonicalityRules.object_canonical_id(enriched),
        )


class BackwardCompatibilityMigrator:
    """
    Handles schema migration for existing triplets without synsets.
    
    Pre-synset triplets have:
    - subject, predicate, object (surface forms only)
    - Maybe polarity + inference_type
    - No synset fields
    
    After migration:
    - Add NULL synset columns
    - Mark provenance as "pre_synset_extraction"
    """
    
    @staticmethod
    def migrate_legacy_triplet(legacy_triplet: Dict) -> Dict:
        """
        Add synset columns to legacy triplet (all NULLs).
        
        Args:
            legacy_triplet: Old triplet schema {"subject": "...", "predicate": "...", "object": "..."}
        
        Returns:
            Migrated triplet with synset columns added
        """
        migrated = dict(legacy_triplet)  # Copy
        
        # Add synset columns (all NULL)
        migrated.update({
            "subject_synsets": None,
            "subject_hypernyms": None,
            "predicate_synsets": None,
            "predicate_hypernyms": None,
            "object_synsets": None,
            "object_hypernyms": None,
            "subject_canonical": None,
            "predicate_canonical": None,
            "object_canonical": None,
            "bm25_subject": None,
            "bm25_predicate": None,
            "bm25_object": None,
            "migration_provenance": "pre_synset_extraction",
        })
        
        return migrated
