#!/usr/bin/env python3
"""Database migration script for GhostProtocol.

Automatically applies SQL migrations from the migrations/ directory
to the configured Supabase database.
"""

import os
import sys
import logging
from pathlib import Path
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_migration_files(migrations_dir: Path) -> list[Path]:
    """Get all .sql migration files sorted by name."""
    if not migrations_dir.exists():
        logger.error(f"Migrations directory not found: {migrations_dir}")
        return []
    
    files = sorted(migrations_dir.glob("*.sql"))
    return files


def create_migrations_table(client: Client) -> None:
    """Create a table to track applied migrations."""
    sql = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        id SERIAL PRIMARY KEY,
        migration_name TEXT UNIQUE NOT NULL,
        applied_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    try:
        client.rpc('exec_sql', {'sql': sql}).execute()
        logger.info("Migrations tracking table created/verified")
    except Exception as e:
        # Fallback: try direct SQL execution if RPC not available
        logger.warning(f"Could not create migrations table via RPC: {e}")
        logger.info("Please create the schema_migrations table manually in Supabase SQL Editor")


def get_applied_migrations(client: Client) -> set[str]:
    """Get list of already applied migration names."""
    try:
        result = client.table('schema_migrations').select('migration_name').execute()
        return {row['migration_name'] for row in result.data}
    except Exception as e:
        logger.warning(f"Could not fetch applied migrations: {e}")
        return set()


def apply_migration(client: Client, migration_file: Path) -> bool:
    """Apply a single migration file."""
    migration_name = migration_file.name
    
    logger.info(f"Applying migration: {migration_name}")
    
    try:
        # Read migration SQL
        sql = migration_file.read_text(encoding='utf-8')
        
        # Execute migration
        # Note: Supabase client doesn't support raw SQL execution directly
        # Users need to run migrations manually via SQL Editor or CLI
        logger.info(f"Migration SQL loaded: {len(sql)} characters")
        logger.warning(
            f"Please apply this migration manually in Supabase SQL Editor:\n"
            f"File: {migration_file}\n"
            f"Or use: supabase db push"
        )
        
        # Record migration as applied (manual confirmation needed)
        response = input(f"Have you applied {migration_name}? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            client.table('schema_migrations').insert({
                'migration_name': migration_name
            }).execute()
            logger.info(f"✓ Migration {migration_name} marked as applied")
            return True
        else:
            logger.info(f"✗ Migration {migration_name} skipped")
            return False
            
    except Exception as e:
        logger.error(f"Failed to apply migration {migration_name}: {e}")
        return False


def run_migrations() -> int:
    """Run all pending migrations."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return 1
    
    # Initialize Supabase client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Connected to Supabase")
    
    # Get migrations directory
    migrations_dir = Path(__file__).parent / "migrations"
    migration_files = get_migration_files(migrations_dir)
    
    if not migration_files:
        logger.warning("No migration files found")
        return 0
    
    logger.info(f"Found {len(migration_files)} migration file(s)")
    
    # Create migrations tracking table
    create_migrations_table(client)
    
    # Get already applied migrations
    applied = get_applied_migrations(client)
    logger.info(f"Already applied: {len(applied)} migration(s)")
    
    # Apply pending migrations
    pending = [f for f in migration_files if f.name not in applied]
    
    if not pending:
        logger.info("✓ All migrations are up to date")
        return 0
    
    logger.info(f"Pending migrations: {len(pending)}")
    
    success_count = 0
    for migration_file in pending:
        if apply_migration(client, migration_file):
            success_count += 1
        else:
            logger.error(f"Migration failed: {migration_file.name}")
            logger.error("Stopping migration process")
            break
    
    logger.info(f"Applied {success_count}/{len(pending)} pending migration(s)")
    return 0 if success_count == len(pending) else 1


if __name__ == "__main__":
    sys.exit(run_migrations())
