# POST -> upload

# Flow:
# Extract text from PDF
# Clean text
# Tokenize
# Store in documents
# Send to indexing
from bson import ObjectId
from pymongo import UpdateOne

from DB.AccessLayer import create_document, delete_pdf_by_file_id, get_stats, update_inverted_index, update_stats 
from DB.mongo import get_db
from services.text_processing import pdf_processing_pipeline
from services.indexing import build_indexing_pipeline

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import traceback
from bson.errors import InvalidId

# Import the orchestrator function we just built
# Adjust the import path based on your project structure!

# Create the router for this controller
router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

@router.post("/upload/")
async def upload_pdf_endpoint(
    # The file itself
    file: UploadFile = File(...),
    
    # Metadata fields coming from the client as form-data
    title: str = Form(...), 
    course: Optional[str] = Form("Unknown"),
    academic_year: Optional[str] = Form("Unknown"),
    department: Optional[str] = Form("Unknown"),
    semester: Optional[str] = Form("Unknown")
):
    # 1. Validate file type
    if not file.filename.lower().endswith('.pdf') or file.content_type != 'application/pdf':
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a valid PDF document.")

    # 2. Package the metadata exactly how our pipeline expects it
    metadata = {
        "title": title,
        "course": course,
        "academic_year": academic_year,
        "department": department,
        "semester": semester
    }

    try:
        # 3. Pass the file stream and metadata to our async orchestrator.
        # file.file provides the underlying Python SpooledTemporaryFile 
        # which has the .read() method PyMuPDF needs!
        doc_id_mapping = await process_and_store_pdf(file.file, metadata)
        
        # 4. Return success response
        return {
            "status": "success",
            "message": f"Successfully processed and indexed {file.filename}",
            "pages_processed": len(doc_id_mapping),
            "data_mapping": doc_id_mapping
        }
        
    except Exception as e:
        # Print the error to your console so you can debug what went wrong
        print(f"Error processing {file.filename}:")
        traceback.print_exc()
        
        # Return a 500 error to the client side
        raise HTTPException(status_code=500, detail=f"An error occurred during processing: {str(e)}")
# Assuming you have the functions from the previous step 
# and your indexing functions (compute_tf, build_inverted_index, etc.) defined above this.

async def process_and_store_pdf(pdf_file, file_metadata: dict):

    """
    Runs the PDF through the IR pipeline and saves the resulting documents,
    inverted index, and stats to MongoDB.
    """
    print(f"1. Extracting and tokenizing PDF: {file_metadata['title']}...")
    
    # 1. Run text processing (from Step 1)
    processed_documents = pdf_processing_pipeline(pdf_file, filename=file_metadata['title'])
    # --- NEW: Generate a unique ID for this entire PDF upload ---
    parent_file_id = ObjectId()
    # Convert to the dictionary format expected by the indexing pipeline
    tokenized_docs_dict = {}

    original_texts_dict = {}
    for index, doc in enumerate(processed_documents):
        local_id = f"page_{index + 1}"
        tokenized_docs_dict[local_id] = doc["tokens"]
        original_texts_dict[local_id] = doc["original_text"]
    
    print("2. Building IR matrices in memory...")
    # 2. Run the indexing pipeline (from Step 2)
    ir_results = build_indexing_pipeline(tokenized_docs_dict)
    

    db = get_db()
    print("3. Saving documents to Database...")
    # 3. Save Documents to DB and keep track of their new MongoDB ObjectIds
    doc_id_mapping = {} # Maps local ID (e.g., "doc_page_1") to MongoDB ObjectId
    docs_to_insert = []
    local_ids_ordered = []
    for local_id, tokens in tokenized_docs_dict.items():

        # Prepare the data dictionary matching your create_document schema
        doc_data = {
            "file_id": parent_file_id, 
            "title": f"{file_metadata['title']} - {local_id}",
            "parent_pdf": file_metadata['title'], 
            "course": file_metadata.get("course", "Unknown"),
            "academic_year": file_metadata.get("academic_year", "Unknown"),
            "department": file_metadata.get("department", "Unknown"),
            "semester": file_metadata.get("semester", "Unknown"),
            
            # Save the readable text
            "content": original_texts_dict[local_id], 
            "tokens_count": ir_results["doc_length"][local_id]
        }
        docs_to_insert.append(doc_data)
        local_ids_ordered.append(local_id)
        # Insert into DB and save the returned ObjectId
        # mongo_id = await create_document(doc_data)
        # doc_id_mapping[local_id] = mongo_id    -----------> because balk problem
    if docs_to_insert:
    # Replace 'db.documents' with your actual collection reference
        insert_result = await db.documents.insert_many(docs_to_insert)
    
    # Map the newly generated ObjectIds back to the local_ids
    for i, mongo_id in enumerate(insert_result.inserted_ids):
        doc_id_mapping[local_ids_ordered[i]] = mongo_id
        

    print("4. Updating Inverted Index in Database...")
    # 4. Save Inverted Index Postings to DB
    # ir_results["inverted_index"] format: {"term": {"local_doc_id": TF, ...}}
    bulk_operations = []
    for term, postings in ir_results["inverted_index"].items():
        # postings is a set, so we iterate through it directly

        # Collect all postings for this specific term across the entire PDF
        batch_postings_for_term = []
        for local_doc_id in postings:
            
            # Get the real MongoDB ID for this document
            mongo_id = doc_id_mapping[local_doc_id]
            
            tf = ir_results["tf"][local_doc_id].get(term, 1)
            
            batch_postings_for_term.append({
                "doc_id": ObjectId(mongo_id), 
                "tf": tf
            })

            # Create ONE update operation per term using $each
            bulk_operations.append(
                UpdateOne(
                    {"_id": term},
                    {
                        "$inc": {"doc_freq": len(batch_postings_for_term)},
                        "$push": {
                            "postings": {
                                "$each": batch_postings_for_term
                            }
                        }
                    },
                    upsert=True
                )
            )
            # Upsert into the DB
            # await update_inverted_index(term, mongo_id, tf) ---> Bulk problem (N+1)
    if bulk_operations:
        BATCH_SIZE = 5000
        for i in range(0, len(bulk_operations), BATCH_SIZE):
            batch = bulk_operations[i:i + BATCH_SIZE]
            await db.inverted_index.bulk_write(batch, ordered=False) 
            # Note: ordered=False allows MongoDB to parallelize the updates internally

    print("5. Updating Global Stats...")
    # 5. Update Global Statistics
    # IMPORTANT: If you are adding multiple PDFs over time, you need to merge 
    # the new stats with the existing DB stats. For now, we update it with the current batch.
    # Let's calculate the stats for this specific PDF manually to avoid KeyErrors
    batch_total_docs = len(doc_id_mapping)
    batch_total_length = sum(ir_results["doc_length"].values())
    batch_avg_length = batch_total_length / batch_total_docs if batch_total_docs > 0 else 0

    existing_stats = await get_stats()
    
    if existing_stats:
        # Get old values from the database (default to 0 if missing)
        old_total_docs = existing_stats.get("total_docs", 0)
        old_avg_length = existing_stats.get("avg_doc_length", 0.0)
        
        # Calculate new combined totals
        new_total_docs = old_total_docs + batch_total_docs
        
        # Reverse-engineer the old total length, add the new length, and calculate the new average
        old_total_length = old_total_docs * old_avg_length
        new_avg_length = (old_total_length + batch_total_length) / new_total_docs
        
        # Update the database
        await update_stats(new_total_docs, new_avg_length)
    else:
        # First time inserting into an empty database
        await update_stats(batch_total_docs, batch_avg_length)

    print("✅ Successfully processed and saved to database!")
    return {k: str(v) for k, v in doc_id_mapping.items()}


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """
    Deletes an entire PDF file and all its associated pages from the database.
    """
    try:
        query_id = ObjectId(file_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid book ID format")
    try:
        # 1. Execute the deletion using your service function
        deleted_count = await delete_pdf_by_file_id(query_id)
        
        # 2. Check if anything was actually deleted
        if deleted_count == 0:
            raise HTTPException(                
                detail="File not found or already deleted."
            )
            
        # 3. Return success response
        return {
            "status": "success",
            "message": f"Successfully deleted {deleted_count} pages associated with the file.",
            "deleted_count": deleted_count
        }
        
    except InvalidId:
        # Catches malformed MongoDB ObjectIds (e.g., "123" instead of a 24-char hex string)
        raise HTTPException(
            detail="Invalid file ID format."
        )
    except HTTPException:
        # Re-raise HTTPExceptions so they aren't caught by the generic Exception block
        raise
    except Exception as e:
        # Log the actual error for your internal debugging
        raise HTTPException(
            detail="An internal server error occurred while attempting to delete the file."
        )
