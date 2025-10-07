from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple

from app.models.book import Book


def _tokenize_subjects(desc: Optional[str]) -> List[str]:
    """
    We appended 'Subjects: a | b | c' to many descriptions.
    Extract them if present for explanations.
    """
    if not desc:
        return []
    m = re.search(r"Subjects:\s*(.*)$", desc, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return []
    tail = m.group(1)
    # split by '|', commas, or newlines; lowercase and strip
    raw = re.split(r"[|\n,]+", tail)
    return [s.strip().lower() for s in raw if s.strip()]


def _keyword_overlap(a: Book, b: Book) -> List[str]:
    sa = set(_tokenize_subjects(getattr(a, "description", None)))
    sb = set(_tokenize_subjects(getattr(b, "description", None)))
    if not sa or not sb:
        return []
    overlap = [s for s in sa & sb if s]
    # keep a few for a readable sentence
    return sorted(overlap)[:5]


def explain_similarity(
    base: Book,
    candidate: Book,
    channel_scores: Dict[str, float],
    approx_cosine: Optional[float] = None,
) -> str:
    """
    Build a short, template-based explanation using:
      - author match
      - subject keyword overlap
      - which channels contributed (cf/semantic)
      - rough cosine if provided
    """
    bits: List[str] = []

    # Author cue
    if base.author and candidate.author and base.author.strip().lower() == candidate.author.strip().lower():
        bits.append(f"same author ({candidate.author})")
    else:
        # shared era / year hint
        if base.published_year and candidate.published_year:
            dy = abs(int(base.published_year) - int(candidate.published_year))
            if dy <= 5:
                bits.append("published in a similar period")

    # Subject overlap cue
    overlap = _keyword_overlap(base, candidate)
    if overlap:
        bits.append("shared subjects: " + ", ".join(overlap))

    # Channels cue
    chs = []
    if channel_scores.get("cf", 0) > 0.01:
        chs.append("liked by similar readers")
    if channel_scores.get("semantic", 0) > 0.01:
        chs.append("close in theme/description")
    if chs:
        bits.append("; ".join(chs))

    # Cosine cue
    if approx_cosine is not None:
        bits.append(f"cosine~{approx_cosine:.3f}")

    if not bits:
        return "Recommended based on overall similarity in themes and readership."

    # small, readable sentence
    return "Because it’s " + "; ".join(bits) + "."
