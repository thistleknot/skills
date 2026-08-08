"""
Synset augmentation orchestrator for multi-stage synset resolution.

Given an extracted triplet (subject/predicate/object as surface phrases),
augments each word with word2vec neighbors + their synsets + first-level hypernyms.

This produces a hierarchical candidate display for LLM synset selection.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from functools import lru_cache
import json

try:
    import numpy as np
except ImportError:
    np = None

try:
    from nltk.corpus import wordnet, stopwords
    from nltk.tokenize import word_tokenize
    from nltk.stem import WordNetLemmatizer
except ImportError:
    wordnet = None
    stopwords = None
    word_tokenize = None
    WordNetLemmatizer = None


@dataclass
class SynsetCandidate:
    """Single synset option for a word, with hypernym context."""
    
    word: str  # Original surface word or word2vec neighbor
    synset_id: str  # e.g., "dog.n.01"
    pos: str  # Part of speech: "n", "v", "a", "r"
    hypernym_id: Optional[str]  # Parent synset, e.g., "canine.n.01"
    hypernym_label: Optional[str]  # Human-readable hypernym, e.g., "canine"
    similarity_score: Optional[float] = None  # If from word2vec, the similarity
    
    def to_dict(self) -> Dict:
        """Format for display to LLM."""
        hyp_str = ""
        if self.hypernym_id and self.hypernym_label:
            hyp_str = f" ({self.hypernym_id})"
        return {
            "word": self.word,
            "synset": self.synset_id,
            "hypernym_chain": [self.synset_id, self.hypernym_id] if self.hypernym_id else [self.synset_id],
            "pos": self.pos,
        }


@dataclass
class WordWithCandidates:
    """All candidates for a single word within an element."""
    
    word: str  # Surface word from extracted triplet
    candidates: List[SynsetCandidate]  # Top-5 candidates (word2vec neighbors with synsets)
    
    def to_dict(self) -> Dict:
        """Format for display to LLM."""
        return {
            "word": self.word,
            "synset_options": [c.to_dict() for c in self.candidates],
        }


@dataclass
class ElementAugmentation:
    """All word+candidate pairs for one element (subject/predicate/object)."""
    
    element_text: str  # Original extracted phrase
    content_words: List[str]  # Filtered content words (no stop words)
    words_with_candidates: List[WordWithCandidates]  # Candidates per word
    
    def to_dict(self) -> Dict:
        """Format for display to LLM."""
        return {
            "element_text": self.element_text,
            "word_options": [w.to_dict() for w in self.words_with_candidates],
        }


class TripletsToAugmentedCandidates:
    """
    Orchestrator: extracted triplet → augmented with word2vec neighbors + synsets + hypernyms.
    
    Pipeline:
    1. Split each element (subject/predicate/object) into tokens
    2. Filter stop words
    3. For each content word:
       - Pull top-5 word2vec neighbors (if available)
       - For each neighbor, lookup synset + first hypernym
       - Format as hierarchical candidate list
    4. Return augmented dict with all candidates keyed by element+word
    """
    
    def __init__(self, word2vec_model=None, use_nltk_stopwords: bool = True, k_neighbors: int = 5):
        """
        Initialize augmentation orchestrator.
        
        Args:
            word2vec_model: Pretrained word2vec model (e.g., gensim.models.Word2Vec).
                           If None, word2vec augmentation is skipped.
            use_nltk_stopwords: Filter common stopwords (requires NLTK).
            k_neighbors: Number of word2vec neighbors to retrieve.
        """
        self.word2vec_model = word2vec_model
        self.k_neighbors = k_neighbors
        self.use_nltk_stopwords = use_nltk_stopwords
        self.lemmatizer = WordNetLemmatizer() if WordNetLemmatizer else None
        
        # Load stopwords
        self.stop_words = set()
        if use_nltk_stopwords and stopwords:
            self.stop_words = set(stopwords.words("english"))
        
    def split_element_into_words(self, element: str) -> List[str]:
        """
        Tokenize phrase → extract content words (filter stop words).
        
        Args:
            element: Surface phrase from extracted triplet, e.g., "the quick brown dog"
        
        Returns:
            List of content words (lowercase, lemmatized if possible)
        """
        # Simple tokenization: lowercase, split on whitespace, filter
        words = element.lower().split()
        
        # Remove stop words
        content_words = []
        for word in words:
            # Strip punctuation (simple approach)
            word_clean = word.strip(".,!?;:\"'")
            if word_clean and word_clean not in self.stop_words:
                content_words.append(word_clean)
        
        return content_words
    
    def get_word2vec_neighbors(self, word: str) -> List[Tuple[str, float]]:
        """
        Retrieve top-k word2vec neighbors for a word.
        
        Args:
            word: Word to expand
        
        Returns:
            List of (neighbor_word, similarity_score) tuples, ordered by similarity (descending)
        """
        if not self.word2vec_model:
            # Fallback: return empty list if no word2vec model
            return []
        
        try:
            # Check if word exists in vocabulary
            if word not in self.word2vec_model.wv:
                return []
            
            # Retrieve neighbors
            neighbors = self.word2vec_model.wv.most_similar(word, topn=self.k_neighbors)
            return neighbors  # Already sorted by similarity descending
        except Exception as e:
            # Silently fail if word2vec lookup errors
            print(f"[WARN] word2vec lookup failed for '{word}': {e}")
            return []
    
    @lru_cache(maxsize=1024)
    def get_synset_for_word(self, word: str) -> Optional[str]:
        """
        Lookup synset ID for a word (most common sense).
        
        Args:
            word: Word to look up
        
        Returns:
            Synset ID string (e.g., "dog.n.01") or None if not found
        """
        if not wordnet:
            return None
        
        try:
            synsets = wordnet.synsets(word)
            if synsets:
                return synsets[0].name()  # Most common sense
        except Exception as e:
            print(f"[WARN] synset lookup failed for '{word}': {e}")
        
        return None
    
    @lru_cache(maxsize=1024)
    def get_hypernym(self, synset_id: str) -> Optional[Tuple[str, str]]:
        """
        Retrieve first-level hypernym for a synset.
        
        Args:
            synset_id: Synset ID string (e.g., "dog.n.01")
        
        Returns:
            Tuple of (hypernym_synset_id, hypernym_label) or None if no hypernym
        """
        if not wordnet:
            return None
        
        try:
            synset = wordnet.synset(synset_id)
            hypernyms = synset.hypernyms()
            if hypernyms:
                hyp = hypernyms[0]  # First hypernym
                return (hyp.name(), hyp.lemma_names()[0])
        except Exception as e:
            print(f"[WARN] hypernym lookup failed for '{synset_id}': {e}")
        
        return None
    
    def get_synset_candidates_for_word(self, word: str) -> List[SynsetCandidate]:
        """
        Build candidate list for a single word.
        
        Strategy:
        1. If word is in word2vec, pull top-5 neighbors
        2. For each neighbor, lookup synset + first hypernym
        3. Also include the word itself if synset found
        4. Return hierarchical candidate list
        
        Args:
            word: Content word from triplet element
        
        Returns:
            List of SynsetCandidate objects
        """
        candidates = []
        
        # First, try the word itself
        synset_id = self.get_synset_for_word(word)
        if synset_id:
            synset = wordnet.synset(synset_id) if wordnet else None
            pos = synset_id.split(".")[-2] if synset_id else "?"
            hyp = self.get_hypernym(synset_id)
            hyp_id, hyp_label = hyp if hyp else (None, None)
            
            candidate = SynsetCandidate(
                word=word,
                synset_id=synset_id,
                pos=pos,
                hypernym_id=hyp_id,
                hypernym_label=hyp_label,
                similarity_score=1.0,  # Perfect match
            )
            candidates.append(candidate)
        
        # Then, add word2vec neighbors
        neighbors = self.get_word2vec_neighbors(word)
        for neighbor_word, similarity in neighbors[:self.k_neighbors]:
            synset_id = self.get_synset_for_word(neighbor_word)
            if synset_id:
                pos = synset_id.split(".")[-2] if synset_id else "?"
                hyp = self.get_hypernym(synset_id)
                hyp_id, hyp_label = hyp if hyp else (None, None)
                
                candidate = SynsetCandidate(
                    word=neighbor_word,
                    synset_id=synset_id,
                    pos=pos,
                    hypernym_id=hyp_id,
                    hypernym_label=hyp_label,
                    similarity_score=similarity,
                )
                candidates.append(candidate)
        
        return candidates[:self.k_neighbors]  # Keep top-5
    
    def augment_element(self, element: str) -> ElementAugmentation:
        """
        Augment a single element (subject/predicate/object) with candidates.
        
        Args:
            element: Surface phrase, e.g., "the quick brown dog"
        
        Returns:
            ElementAugmentation with candidates for each content word
        """
        content_words = self.split_element_into_words(element)
        words_with_candidates = []
        
        for word in content_words:
            candidates = self.get_synset_candidates_for_word(word)
            word_cand = WordWithCandidates(word=word, candidates=candidates)
            words_with_candidates.append(word_cand)
        
        return ElementAugmentation(
            element_text=element,
            content_words=content_words,
            words_with_candidates=words_with_candidates,
        )
    
    def augment_triplet(self, triplet: Dict[str, str]) -> Dict[str, ElementAugmentation]:
        """
        Augment extracted triplet with candidates for all elements.
        
        Args:
            triplet: Dict with keys "subject", "predicate", "object"
        
        Returns:
            Dict with same keys, values are ElementAugmentation objects
        """
        augmented = {}
        for element_key in ["subject", "predicate", "object"]:
            if element_key in triplet:
                augmented[element_key] = self.augment_element(triplet[element_key])
        
        return augmented
    
    def triplet_to_display_format(self, triplet: Dict[str, str]) -> Dict:
        """
        Format augmented triplet for LLM display.
        
        Args:
            triplet: Extracted triplet dict
        
        Returns:
            Nested dict with candidates formatted for LLM readability
        """
        augmented = self.augment_triplet(triplet)
        return {
            "subject": augmented.get("subject").to_dict() if "subject" in augmented else None,
            "predicate": augmented.get("predicate").to_dict() if "predicate" in augmented else None,
            "object": augmented.get("object").to_dict() if "object" in augmented else None,
        }
