"""Automatic migration runner"""
import logging
from alembic import command
from alembic.config import Config
import os

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """
    Run Alembic migrations automatically on startup.
    
    This function runs 'alembic upgrade head' programmatically.
    """
    try:
        # Get the alembic.ini path
        alembic_ini_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "alembic.ini"
        )
        
        if not os.path.exists(alembic_ini_path):
            raise FileNotFoundError(f"alembic.ini not found at {alembic_ini_path}")
        
        # Create Alembic config
        alembic_cfg = Config(alembic_ini_path)
        
        # Run migrations
        logger.info("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}")
        raise
