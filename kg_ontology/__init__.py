"""
KG Ontology Skill - Multi-stage synset resolution with hierarchical hypernyms.

This package implements a two-stage synset resolution pipeline:
1. Extract facts (triplets) from text
2. Augment with word2vec neighbors + synsets + hypernyms
3. LLM selects synsets + hypernym chains per word
4. Enrich triplets with canonical identities

Public API:
- TripletsToAugmentedCandidates: Augmentation orchestrator
- TripletWithChosenSynsets: Final schema with synsets + hypernyms
- SynsetSelectionPromptBuilder: LLM prompt formatter
"""

from synset_augmentation import (
    TripletsToAugmentedCandidates,
    SynsetCandidate,
    WordWithCandidates,
    ElementAugmentation,
)

from synset_selection_schema import (
    ElementSynsetChoices,
    TripletWithChosenSynsets,
    SynsetSelectionPromptBuilder,
)

__version__ = "0.1.0"
__all__ = [
    "TripletsToAugmentedCandidates",
    "SynsetCandidate",
    "WordWithCandidates",
    "ElementAugmentation",
    "ElementSynsetChoices",
    "TripletWithChosenSynsets",
    "SynsetSelectionPromptBuilder",
]
