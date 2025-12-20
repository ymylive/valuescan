#!/usr/bin/env python3
"""
Main entry point for the Process Keepalive Service.

This script initializes and runs the keepalive service that monitors
and automatically restarts unhealthy services.

Usage:
    python keepalive_main.py [--config CONFIG_PATH]
    
Arguments:
    --config, -c    Path to configuration file (default: keepalive_config.json)

Requirements: 1.1
"""

import argparse
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from keepalive.service import KeepaliveService


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='Process Keepalive Service - Monitor and restart unhealthy services',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with default config
    python keepalive_main.py
    
    # Run with custom config path
    python keepalive_main.py --config /etc/valuescan/keepalive.json
    
    # Run with config in current directory
    python keepalive_main.py -c ./my_config.json
"""
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='keepalive_config.json',
        help='Path to configuration file (default: keepalive_config.json)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose (debug) logging'
    )
    
    return parser.parse_args()


def setup_logging(verbose: bool = False) -> None:
    """
    Set up basic logging configuration.
    
    Args:
        verbose: If True, enable debug level logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )


def main() -> int:
    """
    Main entry point.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    args = parse_args()
    
    # Set up logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)
    
    # Resolve config path
    config_path = args.config
    if not os.path.isabs(config_path):
        # Make relative paths relative to script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, config_path)
    
    logger.info(f"Starting Process Keepalive Service")
    logger.info(f"Configuration file: {config_path}")
    
    # Check if config file exists
    if not os.path.exists(config_path):
        logger.warning(f"Configuration file not found: {config_path}")
        logger.warning("Using default configuration (no services configured)")
    
    try:
        # Initialize and run the service
        service = KeepaliveService(config_path)
        service.run()
        return 0
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except SystemExit as e:
        # Re-raise SystemExit to preserve exit code
        raise
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
