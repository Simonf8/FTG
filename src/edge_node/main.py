"""
Main entry point for Edge Node
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.config import get_config, load_config
from src.common.logger import setup_logger, get_logger
from src.common.models import NodeType, Location
from src.edge_node.base import BaseEdgeNode

logger = get_logger(__name__)


async def main():
    """Main entry point for edge node"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Distributed Edge AI Network - Edge Node")
    parser.add_argument("--node-id", required=True, help="Unique node identifier")
    parser.add_argument("--node-type", required=True, choices=["traffic", "crime", "environment", "hybrid"], 
                       help="Type of edge node")
    parser.add_argument("--latitude", type=float, default=0.0, help="Node latitude")
    parser.add_argument("--longitude", type=float, default=0.0, help="Node longitude")
    parser.add_argument("--address", default="", help="Node address")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config) if args.config else get_config()
    
    # Setup logging
    setup_logger(level=args.log_level)
    
    # Create node location
    location = Location(
        latitude=args.latitude,
        longitude=args.longitude,
        address=args.address
    )
    
    # Create edge node
    node = BaseEdgeNode(
        node_id=args.node_id,
        node_type=NodeType(args.node_type),
        location=location,
        config=config
    )
    
    try:
        # Initialize and run the node
        await node.initialize()
        logger.info(f"Edge node {args.node_id} started successfully")
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error running edge node: {e}")
    finally:
        await node.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
