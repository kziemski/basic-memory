"""Add directory column to search_index

Revision ID: a1e32c5f1234
Revises: cc7172b46608
Create Date: 2025-04-09 15:32:10.123456

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1e32c5f1234"
down_revision: Union[str, None] = "cc7172b46608"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a directory column to search_index for faster directory listing.
    
    This adds a directory column to the FTS5 virtual table that stores
    the directory path part of each file_path. This allows for:
    1. Faster directory listing (exact match vs pattern match)
    2. FTS searching on directory paths
    3. More efficient filtering in the directory repository
    """
    print("Running migration for directory column...")
    
    # Simplified migration approach - create backup then restore with new schema
    
    # Step 1: Create backup table with standard schema (not FTS5)
    print("Creating backup table...")
    op.execute("DROP TABLE IF EXISTS search_index_backup")
    op.execute("""
    CREATE TABLE search_index_backup (
        id INTEGER,
        title TEXT,
        content_stems TEXT,
        content_snippet TEXT,
        permalink TEXT,
        file_path TEXT,
        type TEXT,
        from_id INTEGER,
        to_id INTEGER,
        relation_type TEXT,
        entity_id INTEGER,
        category TEXT,
        metadata TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)
    
    # Step 2: Copy all data to the backup table
    print("Copying data to backup table...")
    op.execute("""
    INSERT INTO search_index_backup
    SELECT id, title, content_stems, content_snippet, permalink, file_path, 
           type, from_id, to_id, relation_type, entity_id, category, 
           metadata, created_at, updated_at
    FROM search_index
    """)
        
    # Step 4: Drop the existing search_index table 
    print("Recreating search_index with directory column...")
    op.execute("DROP TABLE IF EXISTS search_index")
    
    # Step 5: Create new FTS5 table with the directory column
    op.execute("""
    CREATE VIRTUAL TABLE search_index USING fts5(
        id UNINDEXED,
        title,
        content_stems,
        content_snippet,
        permalink,
        file_path UNINDEXED,
        directory,
        type UNINDEXED,
        from_id UNINDEXED,
        to_id UNINDEXED,
        relation_type UNINDEXED,
        entity_id UNINDEXED,
        category UNINDEXED,
        metadata UNINDEXED,
        created_at UNINDEXED,
        updated_at UNINDEXED,
        tokenize='unicode61 tokenchars 0x2F',
        prefix='1,2,3,4'
    )
    """)
    
    # Step 6: Insert data back with computed directory column
    print("Restoring data with directory column...")
    op.execute("""
    INSERT INTO search_index (
        id, title, content_stems, content_snippet, permalink, file_path, directory,
        type, from_id, to_id, relation_type, entity_id, category, metadata, 
        created_at, updated_at
    )
    -- get the directory name from the file_path
    SELECT 
        id, title, content_stems, content_snippet, permalink, file_path,
        CASE 
            WHEN type != 'entity' THEN NULL
            ELSE 
            (select '/' || rtrim(
                -- get file path
               rtrim(
                       file_path,
                        -- get filename pathtofile.md -> file.md
                       replace(
                               file_path,
                               -- remove slashes /path/to/file.md -> pathtofile.md
                               rtrim(
                                       file_path,
                                       -- get file name
                                       replace(file_path, '/', '')
                               ),
                               ''
                       )
               ),
               '/'
            ))
        END,
        type, from_id, to_id, relation_type, entity_id, category, metadata, 
        created_at, updated_at
    FROM search_index_backup
    """)
        
    # Step 8: Clean up
    op.execute("DROP TABLE search_index_backup")
    
    print("\n==================================================================")
    print(f"SUCCESS: Added directory column to search_index")
    print("==================================================================\n")


def downgrade() -> None:
    """Restore original search_index schema."""
    # Drop the updated search_index table
    op.execute("DROP TABLE IF EXISTS search_index")

    # Recreate the original search_index without directory column
    op.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
        -- Core entity fields
        id UNINDEXED,          -- Row ID
        title,                 -- Title for searching
        content_stems,         -- Main searchable content split into stems
        content_snippet,       -- File content snippet for display
        permalink,             -- Stable identifier (now indexed for path search)
        file_path UNINDEXED,   -- Physical location
        type UNINDEXED,        -- entity/relation/observation
        
        -- Relation fields 
        from_id UNINDEXED,     -- Source entity
        to_id UNINDEXED,       -- Target entity
        relation_type UNINDEXED, -- Type of relation
        
        -- Observation fields
        entity_id UNINDEXED,   -- Parent entity
        category UNINDEXED,    -- Observation category
        
        -- Common fields
        metadata UNINDEXED,    -- JSON metadata
        created_at UNINDEXED,  -- Creation timestamp
        updated_at UNINDEXED,  -- Last update
        
        -- Configuration
        tokenize='unicode61 tokenchars 0x2F',  -- Hex code for /
        prefix='1,2,3,4'                    -- Support longer prefixes for paths
    );
    """)
    
    # Print instruction for sync
    print("\n------------------------------------------------------------------")
    print("IMPORTANT: After downgrade completes, you need to run:")
    print("basic-memory sync")
    print("------------------------------------------------------------------\n")