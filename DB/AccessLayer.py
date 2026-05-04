from bson import ObjectId
from datetime import datetime
from DB.mongo import get_db

# -----------------------------
# DOCUMENTS COLLECTION
# -----------------------------

async def create_document(data: dict):
    db = get_db()

    document = {
        "file_id" : data["file_id"],
        "title": data["title"],
        "course": data["course"],
        "academic_year": data["academic_year"],
        "department": data["department"],
        "semester": data["semester"],

        "content": data["content"],
        "tokens_count": data["tokens_count"],

        "created_at": datetime.utcnow()
    }

    result = await db.documents.insert_one(document)
    return str(result.inserted_id)


async def get_document_by_id(doc_id: str):
    db = get_db()
    document = await db.documents.find_one({"_id": ObjectId(doc_id)})
    return document

async def delete_pdf_by_file_id(file_id: str):
    db = get_db()
    
    # This deletes EVERY page that shares this file_id in one swoop!
    result = await db.documents.delete_many({"file_id": ObjectId(file_id)})
    
    return result.deleted_count # Returns how many pages were deleted
# -----------------------------
# INVERTED INDEX COLLECTION
# -----------------------------

async def update_inverted_index(term: str, doc_id: str, tf: int):
    db = get_db()

    await db.inverted_index.update_one(
        {"_id": term},
        {
            "$inc": {"doc_freq": 1},
            "$push": {
                "postings": {
                    "doc_id": ObjectId(doc_id),
                    "tf": tf
                }
            }
        },
        upsert=True
    )


async def get_postings(term: str):
    db = get_db()
    term_data = await db.inverted_index.find_one({"_id": term})
    return term_data


# -----------------------------
# EMBEDDINGS COLLECTION
# -----------------------------

async def create_embedding(doc_id: str, vector: list, model: str):
    db = get_db()

    embedding_doc = {
        "doc_id": ObjectId(doc_id),
        "embedding": vector,
        # "model": model,
        "created_at": datetime.utcnow()
    }

    await db.embeddings.insert_one(embedding_doc)


async def get_all_embeddings():
    db = get_db()
    cursor = db.embeddings.find({})
    return await cursor.to_list(length=None)


# -----------------------------
# COLLECTION STATS (BM25)
# -----------------------------

async def update_stats(total_docs: int, avg_doc_length: float):
    db = get_db()

    await db.collection_stats.update_one(
        {"_id": "global"},
        {
            "$set": {
                "total_docs": total_docs,
                "avg_doc_length": avg_doc_length
            }
        },
        upsert=True
    )


async def get_document_lengths(doc_ids: list):
    """Fetches the tokens_count (document length) for a list of document IDs."""
    db = get_db()
    
    # Convert string IDs to MongoDB ObjectIds
    object_ids = [ObjectId(d) for d in doc_ids]
    
    # Only fetch the tokens_count field to save bandwidth
    cursor = db.documents.find({"_id": {"$in": object_ids}}, {"tokens_count": 1})
    
    lengths = {}
    async for doc in cursor:
        lengths[str(doc["_id"])] = doc.get("tokens_count", 1)
        
    return lengths

async def get_stats():
    db = get_db()
    return await db.collection_stats.find_one({"_id": "global"})