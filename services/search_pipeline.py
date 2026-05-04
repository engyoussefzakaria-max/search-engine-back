import math
from collections import defaultdict
from bson import ObjectId

# Import your existing tools!
from services.text_processing import clean_and_tokenize
from DB.AccessLayer import get_postings, get_stats, get_document_by_id, get_document_lengths

# =========================
# Team's BM25 Scoring Engine
# =========================
def bm25_score(
    query_tokens,
    candidate_docs,
    tf_dict,
    idf,
    doc_length,
    avg_dl,
    k1=1.5,
    b=0.75
):
    scores = {}
    for doc_id in candidate_docs:
        score = 0
        dl = doc_length.get(doc_id, 1) # Added .get() just as a safety net

        for term in query_tokens:
            # لو الكلمة مش موجودة في doc
            if term not in tf_dict.get(doc_id, {}):
                continue

            tf = tf_dict[doc_id][term]
            term_idf = idf.get(term, 0)

            numerator = tf * (k1 + 1)
            denominator = (
                tf +
                k1 * (
                    1 - b +
                    b * (dl / avg_dl)
                )
            )
            score += term_idf * (numerator / denominator)
        scores[doc_id] = score
    return scores

# =========================
# Search Execution Pipeline
# =========================
async def execute_search(query_string: str, top_k: int = 5):
    """
    Takes a raw string query, tokenizes it, gathers data from MongoDB,
    runs the Team's BM25 engine, and returns the top results.
    """
    # 1. Clean the query
    query_tokens = clean_and_tokenize(query_string)
    if not query_tokens:
        return []

    # 2. Get global stats
    stats = await get_stats()
    total_docs = stats.get("total_docs", 1) if stats else 1
    avg_dl = stats.get("avg_doc_length", 1.0) if stats else 1.0

    # 3. Gather Data from MongoDB to build the Team's dictionaries
    candidate_docs = set() # update make from DB
    tf_dict = defaultdict(dict)
    idf_dict = {}

    for token in query_tokens:
        term_data = await get_postings(token)
        if not term_data:
            continue 

        df = term_data.get("doc_freq", 1)
        idf_dict[token] = math.log10(total_docs / df) # Building the IDF dict

        for posting in term_data.get("postings", []):
            doc_id = str(posting["doc_id"])
            tf = posting["tf"]
            
            candidate_docs.add(doc_id)      # Building the candidate docs list
            tf_dict[doc_id][token] = tf     # Building the TF dict

    # If no documents contain any of the search words, stop here
    if not candidate_docs:
        return []

    # 4. Fetch the document lengths for only the candidates
    doc_length_dict = await get_document_lengths(list(candidate_docs))

    # 5. --- CALL THE TEAM'S BM25 FUNCTION! ---
    scores = bm25_score(
        query_tokens=query_tokens,
        candidate_docs=list(candidate_docs),
        tf_dict=tf_dict,
        idf=idf_dict,
        doc_length=doc_length_dict,
        avg_dl=avg_dl
    )

    # 6. Sort documents by highest BM25 score
    ranked_docs = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]

    # 7. Fetch the actual content for the top documents to show the user
    results = []
    for doc_id, score in ranked_docs:
        doc_data = await get_document_by_id(doc_id)
        if doc_data:
            raw_file_id = doc_data.get("file_id")
            file_id_str = str(raw_file_id) if raw_file_id else None

            results.append({
                "doc_id": doc_id,
                "file_id" : file_id_str,
                "title": doc_data.get("title"),
                "course" : doc_data.get("course"),
                "academic_year" : doc_data.get("academic_year"),
                "semester" : doc_data.get("semester"),
                "department" : doc_data.get("department"),
                "score": round(score, 4),
                "snippet": doc_data.get("content", "")[:300] + "..."
            })

    return results