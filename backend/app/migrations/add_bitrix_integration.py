"""
Migration script to add Bitrix24 integration support.

Run this script to:
1. Create bitrix_users table
2. Add owner_id and owner_type columns to links table
3. Create necessary indexes

Usage:
    cd backend
    python -m app.migrations.add_bitrix_integration
"""

import sqlite3
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.config import settings


def get_db_path():
    """Extract database path from DATABASE_URL"""
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "")
    return "shortlinks.db"


def run_migration():
    """Run the migration to add Bitrix24 integration support"""
    db_path = get_db_path()
    print(f"Running migration on database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Create bitrix_users table
        print("Creating bitrix_users table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bitrix_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bitrix_user_id VARCHAR(50) NOT NULL,
                bitrix_domain VARCHAR(255) NOT NULL,
                name VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(bitrix_user_id, bitrix_domain)
            )
        """)
        print("  - bitrix_users table created")

        # 2. Check if owner_id column exists in links table
        cursor.execute("PRAGMA table_info(links)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'owner_id' not in columns:
            print("Adding owner_id column to links table...")
            cursor.execute("""
                ALTER TABLE links ADD COLUMN owner_id INTEGER REFERENCES bitrix_users(id)
            """)
            print("  - owner_id column added")
        else:
            print("  - owner_id column already exists")

        if 'owner_type' not in columns:
            print("Adding owner_type column to links table...")
            cursor.execute("""
                ALTER TABLE links ADD COLUMN owner_type VARCHAR(20) DEFAULT 'anonymous'
            """)
            print("  - owner_type column added")
        else:
            print("  - owner_type column already exists")

        # 3. Create index on owner_id
        print("Creating index on owner_id...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_links_owner ON links(owner_id)
            """)
            print("  - idx_links_owner index created")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                print("  - idx_links_owner index already exists")
            else:
                raise

        # 4. Create index on bitrix_users
        print("Creating indexes on bitrix_users...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bitrix_user_domain
                ON bitrix_users(bitrix_user_id, bitrix_domain)
            """)
            print("  - idx_bitrix_user_domain index created")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                print("  - idx_bitrix_user_domain index already exists")
            else:
                raise

        # 5. Add is_qr_click column to clicks table
        cursor.execute("PRAGMA table_info(clicks)")
        click_columns = [col[1] for col in cursor.fetchall()]

        if 'is_qr_click' not in click_columns:
            print("Adding is_qr_click column to clicks table...")
            cursor.execute("""
                ALTER TABLE clicks ADD COLUMN is_qr_click BOOLEAN DEFAULT 0
            """)
            print("  - is_qr_click column added")
        else:
            print("  - is_qr_click column already exists")

        conn.commit()
        print("\nMigration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\nError during migration: {e}")
        raise
    finally:
        conn.close()


def rollback_migration():
    """Rollback the migration (for development purposes)"""
    db_path = get_db_path()
    print(f"Rolling back migration on database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Note: SQLite doesn't support DROP COLUMN directly
        # For a proper rollback, you'd need to recreate the table
        print("Warning: SQLite doesn't support DROP COLUMN")
        print("To fully rollback, you would need to:")
        print("1. Create a new links table without owner_id and owner_type")
        print("2. Copy data from old table to new")
        print("3. Drop old table and rename new one")
        print("\nDropping bitrix_users table...")

        cursor.execute("DROP TABLE IF EXISTS bitrix_users")
        conn.commit()
        print("bitrix_users table dropped")

    except Exception as e:
        conn.rollback()
        print(f"Error during rollback: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Bitrix24 integration migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")

    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
