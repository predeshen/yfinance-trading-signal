"""
Simple scanner service that runs without complex dependencies.
This is a minimal implementation to get the scanner working.
"""
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SimpleScanner:
    """Minimal scanner service"""
    
    def __init__(self, config, data_provider):
        self.config = config
        self.data_provider = data_provider
        self.running = False
    
    async def scan_symbol(self, alias: str, yf_symbol: str):
        """Scan a single symbol"""
        try:
            logger.info(f"Scanning {alias} ({yf_symbol})...")
            
            # Fetch recent data
            h4_df = await self.data_provider.get_candles(
                yf_symbol, "240m", timedelta(days=7)
            )
            
            if not h4_df.empty:
                current_price = h4_df['close'].iloc[-1]
                logger.info(f"  {alias}: ${current_price:.2f}")
            else:
                logger.warning(f"  {alias}: No data available")
                
        except Exception as e:
            logger.error(f"Error scanning {alias}: {e}")
    
    async def run(self):
        """Main scanner loop"""
        self.running = True
        logger.info("Simple scanner started")
        
        while self.running:
            try:
                logger.info("=" * 60)
                logger.info("Starting scan cycle...")
                
                for alias, yf_symbol in self.config.scanner.symbols.items():
                    await self.scan_symbol(alias, yf_symbol)
                
                logger.info("Scan cycle complete")
                logger.info("=" * 60)
                
                # Wait for next scan
                await asyncio.sleep(self.config.scanner.scan_interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Scanner cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scanner loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait before retry
        
        self.running = False
        logger.info("Simple scanner stopped")
    
    def stop(self):
        """Stop the scanner"""
        self.running = False
