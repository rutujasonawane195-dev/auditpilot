"""Policy Document Parsing and TF-IDF Retrieval Tool."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np


def parse_policy_clauses(filepath: str = "data/policy.md") -> List[Dict[str, str]]:
    """Parse policy document into structured clauses by markdown heading.

    Args:
        filepath: Path to policy.md file.

    Returns:
        List of clause dictionaries with keys: clause_id, title, text, header.
    """
    path = Path(filepath)
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")
    # Split on markdown H2 sections: ## <number>. <title> (<Section X.X>)
    sections = re.split(r"(?m)^##\s+", content)
    clauses: List[Dict[str, str]] = []

    for sec in sections[1:]:  # Skip intro header
        lines = sec.strip().split("\n")
        header = lines[0].strip()
        body = "\n".join(lines[1:]).strip()

        # Extract section ID (e.g., "Section 4.1", "Section 5.2")
        sec_match = re.search(r"\((Section\s+[\d\.]+)\)", header)
        if sec_match:
            clause_id = sec_match.group(1)
        else:
            clause_id = header.split(":")[0].strip()

        title = re.sub(r"^\d+\.\s*", "", header)
        title = re.sub(r"\s*\(Section\s+[\d\.]+\)", "", title).strip()

        clauses.append({
            "clause_id": clause_id,
            "title": title,
            "header": header,
            "text": f"{header}\n{body}",
            "body": body,
        })

    return clauses


def retrieve_policy(
    query: str,
    k: int = 3,
    filepath: str = "data/policy.md",
) -> Dict[str, Any]:
    """Retrieve the most relevant policy clauses using TF-IDF similarity.

    Args:
        query: Auditor question or query topic (e.g. 'Sunday postings', 'segregation of duties').
        k: Maximum number of top matching clauses to return (default 3).
        filepath: Path to the policy markdown file.

    Returns:
        Standard tool schema dict with test, flagged_ids, stats, and notes.
    """
    clauses = parse_policy_clauses(filepath)
    if not clauses:
        return {
            "test": "retrieve_policy",
            "flagged_ids": [],
            "stats": {"error": f"Policy file not found or empty: {filepath}"},
            "notes": "Failed: Could not load policy document.",
        }

    corpus = [c["text"] for c in clauses]

    # Try scikit-learn TfidfVectorizer; fallback to numpy TF-IDF if unavailable
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)
        query_vec = vectorizer.transform([query])
        scores = cosine_similarity(query_vec, tfidf_matrix)[0]
    except Exception:
        # Fallback pure-python/numpy TF-IDF
        def tokenize(text: str) -> List[str]:
            return re.findall(r"\b[a-z0-9]+\b", text.lower())

        doc_tokens = [tokenize(doc) for doc in corpus]
        vocab = sorted(list({tok for dt in doc_tokens for tok in dt}))
        vocab_idx = {v: i for i, v in enumerate(vocab)}

        # Document frequencies
        df = np.zeros(len(vocab))
        for dt in doc_tokens:
            for v in set(dt):
                df[vocab_idx[v]] += 1
        idf = np.log((len(corpus) + 1.0) / (df + 1.0)) + 1.0

        # Term frequency matrices
        tf_mat = np.zeros((len(corpus), len(vocab)))
        for i, dt in enumerate(doc_tokens):
            for t in dt:
                tf_mat[i, vocab_idx[t]] += 1
            norm = np.linalg.norm(tf_mat[i])
            if norm > 0:
                tf_mat[i] = tf_mat[i] / norm
        tfidf_matrix = tf_mat * idf

        q_tokens = tokenize(query)
        q_vec = np.zeros(len(vocab))
        for t in q_tokens:
            if t in vocab_idx:
                q_vec[vocab_idx[t]] += 1
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = (q_vec / q_norm) * idf
        scores = np.dot(tfidf_matrix, q_vec)

    # Rank indices by score descending
    ranked_indices = np.argsort(scores)[::-1][:k]

    top_matches = []
    flagged_ids = []
    for rank, idx in enumerate(ranked_indices, start=1):
        clause = clauses[idx]
        score = float(round(float(scores[idx]), 4))
        flagged_ids.append(clause["clause_id"])
        top_matches.append({
            "rank": rank,
            "clause_id": clause["clause_id"],
            "title": clause["title"],
            "score": score,
            "excerpt": clause["body"][:250].strip() + ("..." if len(clause["body"]) > 250 else ""),
            "full_text": clause["text"],
        })

    stats = {
        "query": query,
        "k": k,
        "total_clauses": len(clauses),
        "top_matches": top_matches,
    }

    top_clause = top_matches[0]["clause_id"] if top_matches else "None"
    notes = (
        f"Retrieved {len(top_matches)} policy clauses for query: '{query}'. "
        f"Top match: {top_clause} (score: {top_matches[0]['score'] if top_matches else 0.0})."
    )

    return {
        "test": "retrieve_policy",
        "flagged_ids": flagged_ids,
        "stats": stats,
        "notes": notes,
    }
