# 2. Indexing Pipeline

# Inside indexing.py:

# Build vocabulary
# Compute TF
# Update inverted index
# Compute doc length

import math
import json
import os
from collections import Counter, defaultdict

# =========================
# 2. TF
# =========================
# def compute_tf(tokens):
#     total = len(tokens)
#     counter = Counter(tokens)

#     return {
#         # term: count / total
#         # for term, count in counter.items()
#         counter
#     }
def compute_tf(tokens):
    """Return {term: raw_count} for a token list."""
    return dict(Counter(tokens))

# 3. Inverted Index
# =========================
def build_inverted_index(tokenized_docs):
    inverted = defaultdict(set)

    for doc_id, tokens in tokenized_docs.items():
        for term in set(tokens):
            inverted[term].add(doc_id)

    return inverted


# 4. DF
# =========================
def compute_df(inverted_index):
    return {
        term: len(doc_ids)
        for term, doc_ids in inverted_index.items()
    }

# =========================
# 5. IDF
# =========================
def compute_idf(df, N):
    return {
        term: math.log((N + 1) / (df_val + 1)) + 1
        for term, df_val in df.items()
    }

# =========================
# 6. TF-IDF
# =========================
def compute_tfidf_matrix(tf_dict, idf, min_value=0.0001):
    tfidf_matrix = {}

    for doc_id, tf_scores in tf_dict.items():
        tfidf_matrix[doc_id] = {}

        for term, tf_val in tf_scores.items():
            score = tf_val * idf.get(term, 0)

            if score > min_value:
                tfidf_matrix[doc_id][term] = score

    return tfidf_matrix

# =========================
# 7. Normalization
# =========================
def normalize_tfidf(tfidf_matrix):
    for doc_id, scores in tfidf_matrix.items():
        norm = math.sqrt(sum(v ** 2 for v in scores.values()))

        if norm == 0:
            continue

        for term in scores:
            scores[term] /= norm

    return tfidf_matrix

# =========================
# 8. Stats
# =========================
def compute_global_stats(tokenized_docs, doc_length):
    N = len(tokenized_docs)

    return {
        "num_docs": N,
        "avg_doc_length": sum(doc_length.values()) / N
    }

# =========================
# 10. Pipeline
# =========================
def build_indexing_pipeline(tokenized_docs):

    N = len(tokenized_docs)

    # TF
    tf_dict = {
        doc_id: compute_tf(tokens) # updated here
        for doc_id, tokens in tokenized_docs.items()
    }

    # Inverted Index
    inverted_index = build_inverted_index(tokenized_docs)

    # DF
    df = compute_df(inverted_index)

    # IDF
    idf = compute_idf(df, N)

    # TF-IDF
    tfidf_matrix = compute_tfidf_matrix(tf_dict, idf)

    # Normalize
    tfidf_matrix = normalize_tfidf(tfidf_matrix)

    # Doc length
    doc_length = {
        doc_id: len(tokens)
        for doc_id, tokens in tokenized_docs.items()
    }

    # Stats
    stats = compute_global_stats(tokenized_docs, doc_length)

    

    return {
        "tf": tf_dict,
        "inverted_index": inverted_index,
        "df": df,
        "idf": idf,
        "doc_length": doc_length,
        "tfidf": tfidf_matrix,
        "stats": stats
    }
