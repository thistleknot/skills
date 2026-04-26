"""
Schemas for synset selection phase.

After LLM extracts triplet facts, this phase:
1. Augments each word with word2vec neighbors + synsets + hypernyms
2. Presents candidates to LLM for selection
3. LLM responds with chosen synsets + hypernym chains per word
"""

from typing import Dict, List, Tuple, Optional, Literal
from pydantic import BaseModel, Field


class ElementSynsetChoices(BaseModel):
    """Synset choices for one element (subject/predicate/object)."""
    
    element_text: str = Field(description="Original extracted phrase")
    chosen_synsets: Dict[str, str] = Field(
        description="word → synset_id (e.g., {'dog': 'dog.n.01'})"
    )
    chosen_hypernyms: Dict[str, List[str]] = Field(
        description="word → [current_synset, hypernym] (e.g., {'dog': ['dog.n.01', 'canine.n.01']})"
    )


class TripletWithChosenSynsets(BaseModel):
    """
    Complete extracted triplet with chosen synsets and hypernym chains.
    
    After LLM selects synsets from augmented candidates, this schema
    captures the full triplet with:
    - Surface phrases (subject/predicate/object)
    - Chosen synset per word within each element
    - Hypernym tuple chains (current → next level)
    - Polarity and inference type
    """
    
    subject: str = Field(description="Extracted subject phrase")
    subject_choices: ElementSynsetChoices = Field(description="Synset choices for subject")
    
    predicate: str = Field(description="Extracted predicate phrase")
    predicate_choices: ElementSynsetChoices = Field(description="Synset choices for predicate")
    
    object: str = Field(description="Extracted object phrase")
    object_choices: ElementSynsetChoices = Field(description="Synset choices for object")
    
    polarity: Literal["affirmed", "negated"] = Field(default="affirmed", description="Triplet polarity")
    inference_type: Literal["observed", "inferred"] = Field(default="observed", description="Observation or inference")
    
    def to_canonical_triplet(self) -> Dict:
        """
        Convert to canonical triplet format for storage.
        
        Merges synsets from multi-word elements into tuples.
        Example:
        - subject_synsets: {"quick": "quick.a.01", "dog": "dog.n.01"} → ["quick.a.01", "dog.n.01"]
        - subject_hypernyms: {"quick": ["quick.a.01", "adjective.a.01"], ...}
        """
        return {
            "subject": self.subject,
            "subject_synsets": list(self.subject_choices.chosen_synsets.values()),
            "subject_hypernyms": list(self.subject_choices.chosen_hypernyms.values()),
            "predicate": self.predicate,
            "predicate_synsets": list(self.predicate_choices.chosen_synsets.values()),
            "predicate_hypernyms": list(self.predicate_choices.chosen_hypernyms.values()),
            "object": self.object,
            "object_synsets": list(self.object_choices.chosen_synsets.values()),
            "object_hypernyms": list(self.object_choices.chosen_hypernyms.values()),
            "polarity": self.polarity,
            "inference_type": self.inference_type,
        }


class SynsetSelectionPromptBuilder:
    """
    Builds prompt for LLM synset selection.
    
    Input:
    - Extracted triplet: { "subject": "...", "predicate": "...", "object": "..." }
    - Augmented candidates: { "subject": ElementAugmentation, ... }
    
    Output:
    - Prompt template for LLM to select synsets
    """
    
    @staticmethod
    def format_candidates_for_element(element_augmentation) -> str:
        """Format candidates for a single element into readable display."""
        lines = []
        
        for word_with_candidates in element_augmentation.words_with_candidates:
            lines.append(f"  Word: '{word_with_candidates.word}'")
            
            for i, candidate in enumerate(word_with_candidates.candidates, 1):
                synset_id = candidate.synset_id
                hyp_chain = f" → {candidate.hypernym_id}" if candidate.hypernym_id else ""
                sim_str = f" (similarity: {candidate.similarity_score:.2f})" if candidate.similarity_score else ""
                lines.append(
                    f"    {i}. {synset_id}{hyp_chain}{sim_str}"
                )
        
        return "\n".join(lines)
    
    @staticmethod
    def build_synset_selection_prompt(triplet: Dict, augmented_candidates: Dict) -> str:
        """
        Build full synset selection prompt.
        
        Args:
            triplet: Extracted triplet {"subject": "...", "predicate": "...", "object": "..."}
            augmented_candidates: Augmented candidates {"subject": ElementAugmentation, ...}
        
        Returns:
            Prompt string for LLM
        """
        prompt = """You extracted the following facts from the text:

- subject: "{subject}"
- predicate: "{predicate}"
- object: "{object}"

For each word in each element, choose the best synset from the available options.
The synset options include hierarchy context (current_synset → hypernym).

**SUBJECT "{subject}":**
{subject_candidates}

**PREDICATE "{predicate}":**
{predicate_candidates}

**OBJECT "{object}":**
{object_candidates}

For each word, select ONE synset from its options. If no synset is available or you're unsure, respond with null.

Respond with valid JSON:
{{
  "subject_chosen_synsets": {{"word": "synset_id", ...}},
  "subject_chosen_hypernyms": {{"word": ["synset_id", "hypernym_id"], ...}},
  "predicate_chosen_synsets": {{"word": "synset_id", ...}},
  "predicate_chosen_hypernyms": {{"word": ["synset_id", "hypernym_id"], ...}},
  "object_chosen_synsets": {{"word": "synset_id", ...}},
  "object_chosen_hypernyms": {{"word": ["synset_id", "hypernym_id"], ...}}
}}

Include all words from each element. If a word has no synsets, use null for both synset and hypernym."""
        
        subject_candidates = SynsetSelectionPromptBuilder.format_candidates_for_element(
            augmented_candidates["subject"]
        )
        predicate_candidates = SynsetSelectionPromptBuilder.format_candidates_for_element(
            augmented_candidates["predicate"]
        )
        object_candidates = SynsetSelectionPromptBuilder.format_candidates_for_element(
            augmented_candidates["object"]
        )
        
        return prompt.format(
            subject=triplet["subject"],
            predicate=triplet["predicate"],
            object=triplet["object"],
            subject_candidates=subject_candidates,
            predicate_candidates=predicate_candidates,
            object_candidates=object_candidates,
        )
