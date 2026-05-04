from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from bson.errors import InvalidId
# Assuming you have your DB dependency and response models defined
from DB.AccessLayer import get_db

router = APIRouter()

@router.get("/api/books/{file_id}")
async def get_book(file_id: str, db = Depends(get_db)):
    """
    Retrieves all pages for a specific file_id and reconstructs the book payload.
    """
    # 1. Safely convert the string to a MongoDB ObjectId
    try:
        query_id = ObjectId(file_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid book ID format")
    # 1. Fetch all pages matching the file_id, sorted by creation time (or page_number)
    cursor = db.documents.find({"file_id": query_id}).sort("created_at", 1)
    pages = await cursor.to_list(length=None) 
    
    # 2. Handle 404 if no pages exist
    if not pages:
        raise HTTPException(status_code=404, detail="Book not found")

    # 3. Shape the response payload
    # We grab the metadata from the first page since it's shared across all documents
    first_page = pages[0]
    
    book_response = {
        "file_id": first_page.get("file_id"),
        "title": first_page.get("title"),
        "course": first_page.get("course"),
        "academic_year": first_page.get("academic_year"),
        "department": first_page.get("department"),
        "semester": first_page.get("semester"),
        "total_pages": len(pages),
        "total_tokens": sum(page.get("tokens_count", 0) for page in pages),
        "pages": []
    }

    # 4. Extract just the necessary content for the pages array
    for page in pages:
        book_response["pages"].append({
            "content": page.get("content"),
            "tokens_count": page.get("tokens_count")
            # "page_number": page.get("page_number") <-- Add this once schema is updated
        })

    return serialize_mongo(book_response)

def serialize_mongo(data):
    """
    Recursively iterates through dictionaries and lists, 
    converting any BSON ObjectIds to standard strings.
    """
    if isinstance(data, list):
        return [serialize_mongo(item) for item in data]
    elif isinstance(data, dict):
        return {key: str(value) if isinstance(value, ObjectId) else serialize_mongo(value) for key, value in data.items()}
    return data