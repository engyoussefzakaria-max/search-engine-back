#POST /search?q=process scheduling

#Step 1 — Keyword (BM25)
# tokenize query
# fetch postings
# compute BM25 score

# Step 2 — Semantic
# convert query → embedding
# compute similarity with docs

#Step 3 — Combine keyword + Semantic (Hybrid) 

#Step 4 — Return ranked docs

from fastapi import APIRouter, Query, HTTPException
import traceback

# Import the BM25 execute_search function we just built
from services.search_pipeline import execute_search

# Create the router for the search endpoints
router = APIRouter(prefix="/api/v1/search", tags=["Search"])

@router.get("/")
async def search_endpoint(
    # 'q' is the actual search string typed by the user
    q: str = Query(..., description="Enter your search query here"),
    limit: int = Query(5, ge=1, le=50, description="Number of results to return (1-50)")
):
    """
    Search the indexed PDF documents using the BM25 ranking algorithm.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    try:
        print(f"🔎 Executing BM25 search for: '{q}'")
        
        results = await execute_search(query_string=q, top_k=limit)
        
        return {
            "status": "success",
            "query": q,
            "results_found": len(results),
            "data": results
        }
        
    except Exception as e:
        # Print the full error trace to your terminal for easy debugging
        print(f"Error during search execution:")
        traceback.print_exc()
        
        # Return a clean error to the client
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")