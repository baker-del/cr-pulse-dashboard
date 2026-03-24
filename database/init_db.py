#!/usr/bin/env python3
"""
Database Initialization Script

Creates tables and loads initial data from CSV files
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import Database, get_db


def init_database():
    """Initialize the database with tables and default data"""
    print("🔧 Initializing KPI Dashboard Database...")

    # Get database instance
    db = get_db()

    # Create all tables
    print("Creating tables...")
    db.create_tables()
    print("✅ Tables created successfully")

    # Load targets from CSV
    targets_csv = Path(__file__).parent.parent / 'assets' / 'annual_targets_2026.csv'

    if targets_csv.exists():
        print(f"\nLoading targets from {targets_csv}...")
        try:
            db.load_targets_from_csv(str(targets_csv), year=2026)
            targets = db.get_targets(year=2026)
            print(f"✅ Loaded {len(targets)} KPI targets for 2026")
        except Exception as e:
            print(f"⚠️  Error loading targets: {e}")
    else:
        print(f"⚠️  Targets CSV not found at {targets_csv}")

    print("\n✅ Database initialization complete!")
    print(f"Database location: {os.path.join(os.path.dirname(__file__), 'kpi_dashboard.db')}")


if __name__ == '__main__':
    init_database()
