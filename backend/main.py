import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from this file's directory (backend/)
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
print(f"[STARTUP] .env path: {env_path}, exists: {env_path.exists()}")
print(f"[STARTUP] GROQ_API_KEY loaded: {'Yes' if os.getenv('GROQ_API_KEY') else 'No'}")

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time

from fastapi.middleware.cors import CORSMiddleware
from services.vector_store import VectorStore
import logging

# Import routers
from routes import video, chat, game

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="YTBrain API")

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.2f}ms")
    return response

# CORS setup
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)}
    )

# Include routers
# Include routers with API prefix
app.include_router(video.router, prefix="/api/video")
app.include_router(chat.router, prefix="/api/chat")
app.include_router(game.router, prefix="/api/game")

@app.get("/api/test")
def test():
    return {"status": "backend is running"}

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up YTBrain API (In-Memory Mode)")
    # No database initialization needed for in-memory stores

@app.get("/")
async def root():
    return {"message": "Welcome to YTBrain API"}

@app.get("/health")
async def health_check():
    health_status = {
        "status": "ok", 
        "services": {
            "vector_store": "in-memory (ready)",
            "cache": "in-memory (ready)"
        }
    }
    return health_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=120)
