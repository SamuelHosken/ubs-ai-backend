from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import chat, auth, documents
from app.models import init_db
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0.0",
    description="Sistema de análise de portfólio com IA multi-agente"
)

# Initialize database
logger.info("Initializing database...")
init_db()

# CORS - usar origens do config
allowed_origins = settings.get_allowed_origins_list()
logger.info(f"CORS allowed origins: {allowed_origins}")

# Se está em produção e não tem origens configuradas, permitir todas (temporário para debug)
if settings.ENVIRONMENT == "production" and allowed_origins == ["http://localhost:3000"]:
    logger.warning("⚠️ CORS: No production origins configured, allowing all origins temporarily")
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True if "*" not in allowed_origins else False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Routes
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "UBS Portfolio AI API",
        "status": "running",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
    }

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("=" * 60)
    logger.info(f"🚀 {settings.APP_NAME} Starting...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info(f"OpenAI Model: {settings.OPENAI_MODEL}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    logger.info("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down UBS Portfolio AI...")
