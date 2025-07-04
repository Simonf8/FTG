"""
Main entry point for Central Coordinator
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.config import get_config, load_config
from src.common.logger import setup_logger, get_logger
from src.coordinator.core import CentralCoordinator

logger = get_logger(__name__)


async def main():
    """Main entry point for central coordinator"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Distributed Edge AI Network - Central Coordinator")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config) if args.config else get_config()
    
    # Override config with command line arguments
    config.coordinator.host = args.host
    config.coordinator.port = args.port
    
    # Setup logging
    setup_logger(level=args.log_level)
    
    # Create coordinator
    coordinator = CentralCoordinator(config)
    
    try:
        # Initialize and run the coordinator
        await coordinator.initialize()
        logger.info(f"Central coordinator started on {args.host}:{args.port}")
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error running coordinator: {e}")
    finally:
        await coordinator.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
