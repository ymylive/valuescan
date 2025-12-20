#!/usr/bin/env python3
"""
Database Rebuild Script

Deletes the old simulation database and creates a new one with updated schema.
This is necessary after adding new fields (pyramiding_levels, trailing_stop, etc.)

Usage:
    python simulation/rebuild_database.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulation.database import SimulationDatabase


def rebuild_database(db_path: str = 'simulation.db'):
    """
    Rebuild simulation database with new schema.
    
    WARNING: This will DELETE all existing simulation data!
    
    Args:
        db_path: Path to database file
    """
    db_file = Path(db_path)
    
    # Backup old database if it exists
    if db_file.exists():
        backup_path = db_file.with_suffix('.db.backup')
        print(f"📦 Backing up old database to: {backup_path}")
        
        # If backup already exists, add timestamp
        if backup_path.exists():
            import time
            timestamp = int(time.time())
            backup_path = db_file.with_name(f"{db_file.stem}_{timestamp}.db.backup")
        
        db_file.rename(backup_path)
        print(f"✅ Old database backed up")
    
    # Create new database with updated schema
    print(f"\n🔨 Creating new database: {db_path}")
    db = SimulationDatabase(db_path)
    
    print(f"✅ New database created with updated schema!")
    print(f"\nNew features:")
    print(f"  - Pyramiding TP levels (3%, 5%, 8%)")
    print(f"  - Trailing stop (1.5% callback)")
    print(f"  - Partial close support")
    print(f"  - Signal aggregation (FOMO + Alpha)")
    print(f"\n⚠️  Old database backed up. You can restore it by:")
    print(f"  1. Delete {db_path}")
    print(f"  2. Rename backup file to {db_path}")
    
    db.close()
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Rebuild simulation database")
    parser.add_argument(
        '--db-path',
        default='simulation.db',
        help='Path to database file (default: simulation.db)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    if not args.force:
        print("⚠️  WARNING: This will DELETE all existing simulation data!")
        print(f"Database: {args.db_path}")
        response = input("\nContinue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            sys.exit(0)
    
    rebuild_database(args.db_path)
