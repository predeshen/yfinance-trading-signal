"""
Main application entry point.

This module initializes and runs the trading scanner service.
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("=" * 60)
    logger.info("Trading Scanner Service Starting...")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        from app.config import get_config
        config = get_config()
        logger.info("✓ Configuration loaded")
        
        # Initialize database
        from app.db.database import init_database
        from app.db.migration_runner import run_migrations
        
        init_database(config.database.url)
        logger.info("✓ Database initialized")
        
        # Run migrations
        run_migrations()
        logger.info("✓ Database migrations completed")
        
        # Validate symbols
        from app.data.yfinance_provider import YFinanceMarketDataProvider
        data_provider = YFinanceMarketDataProvider()
        
        logger.info("Validating symbols...")
        for alias, yf_symbol in config.scanner.symbols.items():
            is_valid = await data_provider.validate_symbol(yf_symbol)
            if is_valid:
                logger.info(f"  ✓ {alias} ({yf_symbol})")
            else:
                logger.error(f"  ✗ {alias} ({yf_symbol}) - INVALID")
        
        logger.info("=" * 60)
        logger.info("Trading Scanner Service Started Successfully")
        logger.info(f"Health check available at: http://0.0.0.0:8000/health")
        logger.info("=" * 60)
        
        # Store config in app state
        app.state.config = config
        app.state.data_provider = data_provider
        
        # Start background services
        from app.services.scanner_service import ScannerService
        from app.services.heartbeat_service import HeartbeatService
        from app.services.summary_email_service import SummaryEmailService
        
        scanner_service = ScannerService(config, data_provider)
        heartbeat_service = HeartbeatService(config)
        email_service = SummaryEmailService(config)
        
        # Create background tasks
        scanner_task = asyncio.create_task(scanner_service.run())
        heartbeat_task = asyncio.create_task(heartbeat_service.run())
        email_task = asyncio.create_task(email_service.run())
        
        logger.info("✓ Background services started")
        logger.info(f"  - Scanner: every {config.scanner.scan_interval_seconds}s")
        logger.info(f"  - Heartbeat: every {config.scanner.heartbeat_interval_minutes}m")
        logger.info(f"  - Email Summary: every {config.scanner.email_summary_interval_hours}h")
        
        yield
        
        # Shutdown: cancel background tasks
        logger.info("Stopping background services...")
        scanner_task.cancel()
        heartbeat_task.cancel()
        email_task.cancel()
        
        try:
            await asyncio.gather(scanner_task, heartbeat_task, email_task, return_exceptions=True)
        except asyncio.CancelledError:
            pass
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        raise
    
    # Shutdown
    logger.info("Trading Scanner Service Shutting Down...")


# Create FastAPI app
app = FastAPI(
    title="Trading Scanner Service",
    description="Production-ready trading scanner with H4 FVG/OB strategy",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Trading Scanner",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON with health status
    """
    try:
        # Check database connection
        from app.db.database import get_engine
        from sqlalchemy import text
        
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Overall status
    is_healthy = db_status == "healthy"
    
    response = {
        "status": "healthy" if is_healthy else "unhealthy",
        "database": db_status,
        "service": "running"
    }
    
    status_code = 200 if is_healthy else 503
    return JSONResponse(content=response, status_code=status_code)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
