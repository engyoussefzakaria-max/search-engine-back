from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import settings
from DB.mongo import connect_to_mongo, close_mongo_connection
from controllers.upload import router as upload_router
from controllers.search import router as search_router
from controllers.book import router as book_router
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "https://svnu-search.vercel.app" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  
    allow_methods=["*"],        
    allow_headers=["*"],        
)
app.include_router(upload_router)
app.include_router(search_router)  
app.include_router(book_router)  


