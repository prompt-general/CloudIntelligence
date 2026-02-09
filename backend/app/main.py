from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine, SessionLocal
from app.auth import router as auth_router
from app.api import v1
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    logger.info("Starting CloudIntelligence API...")
    # Initialize database
    from app.database import init_db
    await init_db()
    
    # Initialize Neo4j
    try:
        from app.core.neo4j_client import neo4j_client
        neo4j_client.connect()
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j on startup: {e}")
    
    yield
    
    logger.info("Shutting down CloudIntelligence API...")
    # Cleanup
    await engine.dispose()
    try:
        from app.core.neo4j_client import neo4j_client
        neo4j_client.close()
    except Exception as e:
        logger.error(f"Error closing Neo4j connection: {e}")

app = FastAPI(
    title="CloudIntelligence API",
    description="AI-powered cloud intelligence platform",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(v1.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "name": "CloudIntelligence API",
        "version": "0.1.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}