"""
Migration script to add analytics fields to existing database.
Run this script once after deploying the new code to add new columns and indexes.

Usage:
    python -m app.migrations.add_analytics_fields
"""

import sqlite3
import os


def migrate(db_path: str = None):
    """Add analytics columns and indexes to existing database"""
    if db_path is None:
        # Default to the database in the data directory
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'shortlinks.db')

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Migration not needed for new database.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Running migration on {db_path}")

    # Add new columns to clicks table
    columns_to_add_clicks = [
        ("country_code", "VARCHAR(2)"),
        ("country_name", "VARCHAR(100)"),
        ("city", "VARCHAR(100)"),
        ("is_unique", "BOOLEAN DEFAULT 1"),
    ]

    for col_name, col_type in columns_to_add_clicks:
        try:
            cursor.execute(f"ALTER TABLE clicks ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} to clicks table")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"Column {col_name} already exists in clicks table")
            else:
                raise

    # Add unique_clicks_count to links table
    try:
        cursor.execute("ALTER TABLE links ADD COLUMN unique_clicks_count INTEGER DEFAULT 0")
        print("Added column unique_clicks_count to links table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("Column unique_clicks_count already exists in links table")
        else:
            raise

    # Create unique_visitors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unique_visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            ip_address VARCHAR(45) NOT NULL,
            user_agent_hash VARCHAR(64) NOT NULL,
            visit_date DATE NOT NULL,
            first_click_id INTEGER,
            FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE,
            FOREIGN KEY (first_click_id) REFERENCES clicks(id) ON DELETE SET NULL,
            UNIQUE (link_id, ip_address, user_agent_hash, visit_date)
        )
    """)
    print("Created unique_visitors table")

    # Create indexes
    indexes = [
        ("idx_clicks_link_time", "clicks", "link_id, clicked_at"),
        ("idx_clicks_link_country", "clicks", "link_id, country_code"),
        ("idx_unique_visitors_lookup", "unique_visitors", "link_id, ip_address, user_agent_hash, visit_date"),
    ]

    for idx_name, table, columns in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
            print(f"Created index {idx_name}")
        except sqlite3.OperationalError as e:
            print(f"Index {idx_name}: {e}")

    conn.commit()
    conn.close()

    print("Migration completed successfully!")


if __name__ == "__main__":
    migrate()
