#!/usr/bin/env python3
"""
Migration Runner for Enhanced Memory System
Applies the memory system database schema changes
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import engine, SessionLocal
from database_models import Base
import sqlalchemy as sa


def run_migration():
    """Run the memory system migration"""
    print("=" * 80)
    print("Enhanced Agent Memory System - Database Migration")
    print("=" * 80)
    print()
    
    # Read migration SQL
    migration_file = Path(__file__).parent / "add_memory_system.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"📄 Reading migration from: {migration_file}")
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    # Split into individual statements
    statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]
    
    print(f"📊 Found {len(statements)} SQL statements to execute")
    print()
    
    # Execute migration
    db = SessionLocal()
    success_count = 0
    error_count = 0
    
    try:
        for i, statement in enumerate(statements, 1):
            # Skip comments and empty statements
            if not statement or statement.startswith('--'):
                continue
            
            try:
                # Show progress
                if 'CREATE TABLE' in statement:
                    table_name = statement.split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()
                    print(f"[{i}/{len(statements)}] Creating table: {table_name}")
                elif 'INSERT INTO' in statement:
                    print(f"[{i}/{len(statements)}] Inserting initial data...")
                elif 'CREATE INDEX' in statement:
                    print(f"[{i}/{len(statements)}] Creating index...")
                else:
                    print(f"[{i}/{len(statements)}] Executing statement...")
                
                # Execute statement
                db.execute(sa.text(statement))
                db.commit()
                success_count += 1
                
            except Exception as e:
                error_msg = str(e)
                # Ignore "table already exists" errors
                if 'already exists' in error_msg.lower():
                    print(f"  ⚠️  Table already exists, skipping...")
                    success_count += 1
                else:
                    print(f"  ❌ Error: {error_msg}")
                    error_count += 1
                    db.rollback()
        
        print()
        print("=" * 80)
        print("Migration Summary")
        print("=" * 80)
        print(f"✅ Successful: {success_count}")
        print(f"❌ Errors: {error_count}")
        print()
        
        if error_count == 0:
            print("🎉 Migration completed successfully!")
            return True
        else:
            print("⚠️  Migration completed with errors")
            return False
            
    except Exception as e:
        print(f"\n❌ Fatal error during migration: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def verify_tables():
    """Verify that all memory tables were created"""
    print()
    print("=" * 80)
    print("Verifying Memory System Tables")
    print("=" * 80)
    print()
    
    expected_tables = [
        'episode_memories',
        'semantic_memories',
        'user_memory_profiles',
        'memory_consolidations',
        'memory_embeddings',
        'agent_performance_metrics',
        'memory_retrieval_log'
    ]
    
    db = SessionLocal()
    
    try:
        inspector = sa.inspect(engine)
        existing_tables = inspector.get_table_names()
        
        all_exist = True
        for table in expected_tables:
            if table in existing_tables:
                print(f"✅ {table}")
            else:
                print(f"❌ {table} - NOT FOUND")
                all_exist = False
        
        print()
        if all_exist:
            print("🎉 All memory system tables verified!")
            return True
        else:
            print("⚠️  Some tables are missing")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying tables: {e}")
        return False
    finally:
        db.close()


def show_table_info():
    """Show information about created tables"""
    print()
    print("=" * 80)
    print("Memory System Table Information")
    print("=" * 80)
    print()
    
    db = SessionLocal()
    
    try:
        # Count records in each table
        from database_models import (
            EpisodeMemory, SemanticMemory, UserMemoryProfile,
            MemoryConsolidation, MemoryEmbedding, AgentPerformanceMetric,
            MemoryRetrievalLog
        )
        
        tables = [
            ('Episode Memories', EpisodeMemory),
            ('Semantic Memories', SemanticMemory),
            ('User Profiles', UserMemoryProfile),
            ('Consolidations', MemoryConsolidation),
            ('Embeddings', MemoryEmbedding),
            ('Performance Metrics', AgentPerformanceMetric),
            ('Retrieval Logs', MemoryRetrievalLog),
        ]
        
        for name, model in tables:
            try:
                count = db.query(model).count()
                print(f"📊 {name:25} {count:5} records")
            except Exception as e:
                print(f"⚠️  {name:25} Error: {e}")
        
        print()
        
    except Exception as e:
        print(f"❌ Error getting table info: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print()
    print("🚀 Starting Enhanced Memory System Migration")
    print()
    
    # Run migration
    success = run_migration()
    
    if success:
        # Verify tables
        verify_tables()
        
        # Show table info
        show_table_info()
        
        print("=" * 80)
        print("✅ Migration Complete!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Implement memory services (Phase 1.2)")
        print("2. Integrate embedding service (Phase 1.3)")
        print("3. Test memory system (Phase 1.4)")
        print()
    else:
        print("=" * 80)
        print("❌ Migration Failed")
        print("=" * 80)
        print()
        print("Please check the errors above and fix any issues.")
        print()
        sys.exit(1)