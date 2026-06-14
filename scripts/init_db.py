"""Initialize the database and create all tables."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.engine import init_database
from config.settings import DB_PATH, DATA_DIR, CACHE_DIR


def main():
    """Initialize database and ensure directories exist."""
    print("=" * 60)
    print("  基金投资顾问系统 - 数据库初始化")
    print("=" * 60)
    print()

    # Ensure directories
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Data directory: {DATA_DIR}")
    print(f"  Cache directory: {CACHE_DIR}")
    print(f"  Database path: {DB_PATH}")
    print()

    # Create tables
    print("  Creating database tables...")
    init_database()
    print()
    print("  Database initialized successfully!")
    print()
    print("  Next steps:")
    print("    1. Run: python scripts/backfill_data.py    # to fetch historical data")
    print("    2. Run: python -m src.cli.main fetch all   # to update data")
    print("    3. Run: python -m src.cli.main --help      # to see commands")
    print("=" * 60)


if __name__ == "__main__":
    main()
