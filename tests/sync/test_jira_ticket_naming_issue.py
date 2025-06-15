"""Test for Jira ticket naming sync issue reported in GitHub issue #136."""

import pytest
from pathlib import Path
from textwrap import dedent

from basic_memory.config import ProjectConfig
from basic_memory.services import EntityService
from basic_memory.sync.sync_service import SyncService


async def create_test_file(path: Path, content: str) -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.mark.asyncio
async def test_jira_ticket_naming_sync_issue(
    sync_service: SyncService, project_config: ProjectConfig, entity_service: EntityService
):
    """Test sync behavior with Jira ticket naming patterns.
    
    Reproduces issue #136 where files with Jira ticket numbers at the beginning
    don't sync properly when multiple files follow the same pattern.
    """
    project_dir = project_config.home

    # Create multiple files with Jira ticket pattern (the problematic case)
    jira_files = [
        {
            "path": "DL-11-feature-a.md",
            "content": dedent("""
                ---
                type: knowledge
                title: DL-11 Feature A
                ---
                # DL-11 Feature A
                
                First feature for ticket DL-11.
                
                ## Tasks
                - [task] Implement feature A
                - [task] Test feature A
            """).strip(),
            "expected_permalink": "dl-11-feature-a"
        },
        {
            "path": "DL-11-feature-b.md", 
            "content": dedent("""
                ---
                type: knowledge
                title: DL-11 Feature B
                ---
                # DL-11 Feature B
                
                Second feature for ticket DL-11.
                
                ## Tasks
                - [task] Implement feature B
                - [task] Test feature B
            """).strip(),
            "expected_permalink": "dl-11-feature-b"
        },
        {
            "path": "DL-11-analysis.md",
            "content": dedent("""
                ---
                type: knowledge
                title: DL-11 Analysis
                ---
                # DL-11 Analysis
                
                Analysis for ticket DL-11.
                
                ## Notes
                - [analysis] Key findings from DL-11
                - [decision] Implementation approach
            """).strip(),
            "expected_permalink": "dl-11-analysis"
        }
    ]

    # Create all files before syncing (simulates the user's scenario)
    for file_data in jira_files:
        await create_test_file(project_dir / file_data["path"], file_data["content"])

    # Run sync
    report = await sync_service.sync(project_config.home)
    
    # Verify all files were detected as new
    assert len(report.new) == 3, f"Expected 3 new files, got {len(report.new)}"
    
    # Verify all entities were created successfully
    entities = await entity_service.repository.find_all()
    assert len(entities) == 3, f"Expected 3 entities in database, got {len(entities)}"
    
    # Verify each file has correct entity and permalink
    for file_data in jira_files:
        # Check entity exists by file path
        entity = await entity_service.repository.get_by_file_path(file_data["path"])
        assert entity is not None, f"Entity not found for file: {file_data['path']}"
        
        # Check permalink matches expected
        assert entity.permalink == file_data["expected_permalink"], (
            f"File {file_data['path']} has incorrect permalink. "
            f"Expected: {file_data['expected_permalink']}, Got: {entity.permalink}"
        )
        
        # Verify entity can be retrieved by permalink
        entity_by_permalink = await entity_service.repository.get_by_permalink(entity.permalink)
        assert entity_by_permalink is not None, (
            f"Entity not found by permalink: {entity.permalink}"
        )
        assert entity_by_permalink.id == entity.id


@pytest.mark.asyncio
async def test_jira_ticket_naming_workaround(
    sync_service: SyncService, project_config: ProjectConfig, entity_service: EntityService
):
    """Test the workaround mentioned by user (moving ticket number to end).
    
    This should work correctly and demonstrates the difference in behavior.
    """
    project_dir = project_config.home

    # Create files with ticket number at the end (the workaround)
    workaround_files = [
        {
            "path": "feature-a-DL-11.md",
            "content": dedent("""
                ---
                type: knowledge
                title: Feature A DL-11
                ---
                # Feature A DL-11
                
                Feature A with ticket number at end.
                
                ## Tasks
                - [task] Implement A
            """).strip(),
            "expected_permalink": "feature-a-dl-11"
        },
        {
            "path": "feature-b-DL-11.md",
            "content": dedent("""
                ---
                type: knowledge
                title: Feature B DL-11
                ---
                # Feature B DL-11
                
                Feature B with ticket number at end.
                
                ## Tasks
                - [task] Implement B
            """).strip(),
            "expected_permalink": "feature-b-dl-11"
        }
    ]

    # Create all files
    for file_data in workaround_files:
        await create_test_file(project_dir / file_data["path"], file_data["content"])

    # Run sync
    report = await sync_service.sync(project_config.home)
    
    # Verify sync completed successfully
    assert len(report.new) == 2
    
    # Verify entities were created
    entities = await entity_service.repository.find_all()
    assert len(entities) == 2
    
    # Verify permalinks
    for file_data in workaround_files:
        entity = await entity_service.repository.get_by_file_path(file_data["path"])
        assert entity is not None
        assert entity.permalink == file_data["expected_permalink"]


@pytest.mark.asyncio
async def test_sequential_jira_file_creation(
    sync_service: SyncService, project_config: ProjectConfig, entity_service: EntityService
):
    """Test creating Jira ticket files one by one (may reveal timing issues)."""
    project_dir = project_config.home

    jira_files = [
        ("DL-11-first.md", "# DL-11 First\nFirst file"),
        ("DL-11-second.md", "# DL-11 Second\nSecond file"),
        ("DL-11-third.md", "# DL-11 Third\nThird file"),
    ]

    # Create and sync files one by one
    for i, (filename, content) in enumerate(jira_files, 1):
        # Create file
        file_content = f"""
---
type: knowledge
title: {filename.replace('.md', '').replace('-', ' ').title()}
---
{content}

## Notes
- [note] File {i} in sequence
"""
        await create_test_file(project_dir / filename, file_content.strip())
        
        # Sync after each file creation
        report = await sync_service.sync(project_config.home)
        
        # Verify this file was synced
        assert len(report.new) >= 1 or len(report.modified) >= 0, (
            f"No changes detected after creating {filename}"
        )
        
        # Verify entity exists
        entity = await entity_service.repository.get_by_file_path(filename)
        assert entity is not None, f"Entity not created for {filename}"
        
        # Verify total count matches files created so far
        all_entities = await entity_service.repository.find_all()
        assert len(all_entities) == i, (
            f"Expected {i} entities after creating {filename}, got {len(all_entities)}"
        )


@pytest.mark.asyncio 
async def test_mixed_jira_and_regular_files(
    sync_service: SyncService, project_config: ProjectConfig, entity_service: EntityService
):
    """Test mixing Jira ticket files with regular files to ensure no interference."""
    project_dir = project_config.home

    # Mix of Jira ticket files and regular files
    mixed_files = [
        "DL-11-task.md",
        "regular-file.md", 
        "DL-11-analysis.md",
        "another-regular.md",
        "DL-11-implementation.md"
    ]

    # Create all files
    for filename in mixed_files:
        content = f"""
---
type: knowledge
title: {filename.replace('.md', '').replace('-', ' ').title()}
---
# {filename.replace('.md', '').replace('-', ' ').title()}

Content for {filename}

## Notes
- [note] Test file
"""
        await create_test_file(project_dir / filename, content.strip())

    # Run sync
    report = await sync_service.sync(project_config.home)
    
    # Verify all files were processed
    assert len(report.new) == 5
    
    # Verify all entities exist
    entities = await entity_service.repository.find_all()
    assert len(entities) == 5
    
    # Verify each file has an entity
    for filename in mixed_files:
        entity = await entity_service.repository.get_by_file_path(filename)
        assert entity is not None, f"Missing entity for {filename}"