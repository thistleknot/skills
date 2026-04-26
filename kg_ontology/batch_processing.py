"""
Batch processing for multiple triplets.

Handles the complete pipeline:
1. Extract many triplets from 1 string (LLM call 1)
2. Augment all triplets locally
3. Select synsets for all triplets (LLM call 2)
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass

from synset_augmentation import TripletsToAugmentedCandidates, ElementAugmentation
from synset_selection_schema import (
    TripletWithChosenSynsets,
    SynsetSelectionPromptBuilder,
)
from triplet_enrichment import (
    EnrichedTriplet,
    TripletEnricher,
    CanonicalityRules,
)


@dataclass
class BatchAugmentationResult:
    """Result of augmenting multiple triplets."""
    
    triplets: List[Dict[str, str]]  # Original extracted triplets
    augmented: List[Dict]  # Augmented with candidates
    
    def to_llm_format(self) -> str:
        """Format for LLM synset selection prompt."""
        lines = ["Select synsets for the following triplets:\n"]
        
        for i, (triplet, aug) in enumerate(zip(self.triplets, self.augmented), 1):
            lines.append(f"\n=== Triplet {i} ===")
            lines.append(f"Subject: {triplet['subject']}")
            lines.append(f"Predicate: {triplet['predicate']}")
            lines.append(f"Object: {triplet['object']}")
            lines.append("")
            
            # Format candidates
            for element_key in ["subject", "predicate", "object"]:
                element_aug = aug[element_key]
                lines.append(f"{element_key.upper()}:")
                for word_opt in element_aug["word_options"]:
                    lines.append(f"  Word: {word_opt['word']}")
                    for synset_opt in word_opt["synset_options"]:
                        lines.append(
                            f"    - {synset_opt['synset']} → "
                            f"{synset_opt['hypernym_chain'][1] if len(synset_opt['hypernym_chain']) > 1 else 'root'}"
                        )
                lines.append("")
        
        return "\n".join(lines)


@dataclass
class BatchEnrichmentResult:
    """Result of enriching multiple triplets with synsets."""
    
    enriched_triplets: List[EnrichedTriplet]
    canonical_triplets: List[Tuple[str, str, str]]
    
    def to_dict_list(self) -> List[Dict]:
        """Convert to list of dicts for storage."""
        return [triplet.to_dict() for triplet in self.enriched_triplets]


class BatchSynsetOrchestrator:
    """
    Orchestrates batch synset resolution for multiple triplets.
    
    Pipeline:
    1. Augment: multiple triplets → augmented with candidates
    2. Select: LLM chooses synsets for all
    3. Enrich: merge choices back to triplets
    """
    
    def __init__(self, word2vec_model=None, k_neighbors: int = 5):
        """Initialize orchestrator."""
        self.augmentor = TripletsToAugmentedCandidates(
            word2vec_model=word2vec_model,
            use_nltk_stopwords=True,
            k_neighbors=k_neighbors,
        )
    
    def augment_batch(self, triplets: List[Dict[str, str]]) -> BatchAugmentationResult:
        """
        Augment multiple triplets with word2vec candidates.
        
        Args:
            triplets: List of extracted triplets, each with subject/predicate/object
        
        Returns:
            BatchAugmentationResult with augmented candidates
        """
        augmented = []
        
        for triplet in triplets:
            aug_dict = self.augmentor.triplet_to_display_format(triplet)
            augmented.append(aug_dict)
        
        return BatchAugmentationResult(triplets=triplets, augmented=augmented)
    
    def build_batch_selection_prompt(
        self, batch_result: BatchAugmentationResult
    ) -> str:
        """
        Build LLM prompt for selecting synsets for all triplets.
        
        Args:
            batch_result: BatchAugmentationResult from augment_batch
        
        Returns:
            Prompt string for LLM
        """
        return batch_result.to_llm_format()
    
    def enrich_batch(
        self,
        batch_result: BatchAugmentationResult,
        llm_responses: List[TripletWithChosenSynsets],
    ) -> BatchEnrichmentResult:
        """
        Enrich multiple triplets with LLM's synset choices.
        
        Args:
            batch_result: Original augmentation result
            llm_responses: List of LLM synset selections (one per triplet)
        
        Returns:
            BatchEnrichmentResult with enriched triplets + canonical forms
        """
        if len(llm_responses) != len(batch_result.triplets):
            raise ValueError(
                f"Number of LLM responses ({len(llm_responses)}) must match "
                f"number of triplets ({len(batch_result.triplets)})"
            )
        
        enriched_triplets = []
        canonical_triplets = []
        
        for extracted, llm_response in zip(batch_result.triplets, llm_responses):
            # Enrich
            enriched = TripletEnricher.enrich_from_llm_response(
                extracted, llm_response
            )
            
            # Validate
            errors = TripletEnricher.validate_enrichment(enriched)
            if errors:
                raise ValueError(f"Enrichment validation failed: {errors}")
            
            # Get canonical
            canonical = CanonicalityRules.canonical_triplet(enriched)
            
            enriched_triplets.append(enriched)
            canonical_triplets.append(canonical)
        
        return BatchEnrichmentResult(
            enriched_triplets=enriched_triplets,
            canonical_triplets=canonical_triplets,
        )
    
    def process_batch(
        self,
        triplets: List[Dict[str, str]],
        llm_responses: List[TripletWithChosenSynsets],
    ) -> BatchEnrichmentResult:
        """
        End-to-end batch processing: augment → enrich → canonicalize.
        
        Args:
            triplets: Extracted triplets from LLM
            llm_responses: LLM's synset selections for each triplet
        
        Returns:
            BatchEnrichmentResult ready for storage
        """
        batch_aug = self.augment_batch(triplets)
        batch_enriched = self.enrich_batch(batch_aug, llm_responses)
        return batch_enriched


class BatchSelectionPromptBuilder:
    """Builds prompts for batch synset selection."""
    
    @staticmethod
    def build_prompt_for_batch(
        triplets: List[Dict[str, str]],
        augmented_batch: BatchAugmentationResult,
    ) -> str:
        """
        Build LLM prompt for batch synset selection.
        
        Args:
            triplets: Original extracted triplets
            augmented_batch: Augmented results
        
        Returns:
            Prompt string
        """
        lines = [
            "You extracted the following facts from the text.",
            "For EACH triplet, select the best synsets from the available options.",
            "Show hierarchy context (current_synset → hypernym) to understand taxonomy.\n",
        ]
        
        for i, (triplet, aug) in enumerate(zip(triplets, augmented_batch.augmented), 1):
            lines.append(f"\n{'='*60}")
            lines.append(f"Triplet {i}")
            lines.append(f"{'='*60}")
            
            lines.append(f"Extracted:")
            lines.append(f"  subject: {triplet['subject']}")
            lines.append(f"  predicate: {triplet['predicate']}")
            lines.append(f"  object: {triplet['object']}\n")
            
            # Subject
            lines.append(f"SUBJECT: {triplet['subject']}")
            subject_aug = aug["subject"]["word_options"]
            for word_opt in subject_aug:
                lines.append(f"  Word: '{word_opt['word']}'")
                for j, synset_opt in enumerate(word_opt["synset_options"], 1):
                    chain_str = " → ".join(synset_opt["hypernym_chain"])
                    lines.append(f"    {j}. {chain_str}")
            
            # Predicate
            lines.append(f"\nPREDICATE: {triplet['predicate']}")
            pred_aug = aug["predicate"]["word_options"]
            for word_opt in pred_aug:
                lines.append(f"  Word: '{word_opt['word']}'")
                for j, synset_opt in enumerate(word_opt["synset_options"], 1):
                    chain_str = " → ".join(synset_opt["hypernym_chain"])
                    lines.append(f"    {j}. {chain_str}")
            
            # Object
            lines.append(f"\nOBJECT: {triplet['object']}")
            obj_aug = aug["object"]["word_options"]
            for word_opt in obj_aug:
                lines.append(f"  Word: '{word_opt['word']}'")
                for j, synset_opt in enumerate(word_opt["synset_options"], 1):
                    chain_str = " → ".join(synset_opt["hypernym_chain"])
                    lines.append(f"    {j}. {chain_str}")
        
        # Instructions
        lines.append(f"\n{'='*60}")
        lines.append("INSTRUCTIONS")
        lines.append(f"{'='*60}")
        lines.append("""
Respond with valid JSON array, one object per triplet:
[
  {
    "triplet_index": 0,
    "subject_chosen_synsets": {"word": "synset_id", ...},
    "subject_chosen_hypernyms": {"word": ["synset_id", "hypernym_id"], ...},
    "predicate_chosen_synsets": {"word": "synset_id", ...},
    "predicate_chosen_hypernyms": {"word": ["synset_id", "hypernym_id"], ...},
    "object_chosen_synsets": {"word": "synset_id", ...},
    "object_chosen_hypernyms": {"word": ["synset_id", "hypernym_id"], ...}
  },
  ...
]

For each word in each element, select ONE synset from the options above.
If no synset available, use null.
Preserve all hierarchical relationships.""")
        
        return "\n".join(lines)
