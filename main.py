from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.db import create_db_and_tables #, engine # engine might not be needed directly here
from src.routers import tee_times_router # We'll create this next

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    print("Creating database and tables...")
    create_db_and_tables()
    yield
    # Code to run on shutdown (if any)

app = FastAPI(
    title="Tee Time API",
    version="0.1.0",
    description="API for accessing and managing golf tee times scraped from various public sources. Provides endpoints to trigger scraping and read course and tee time information.",
    lifespan=lifespan
)

app.include_router(tee_times_router.router, prefix="/api/v1")

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Tee Time API. Navigate to /docs for API documentation."}

if __name__ == "__main__":
    import uvicorn
    # Note: This is for local development. For production, use a process manager.
    # The old main() function that runs scraping is no longer called here directly.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) # Added reload=True and "main:app" for uvicorn CLI
