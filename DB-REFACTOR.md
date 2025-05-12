# App-Level Database Refactoring

This document outlines the plan for migrating Basic Memory from per-project SQLite databases to a single app-level database that manages all knowledge data across projects.

## Goals

- Move to a single app-level SQLite database for all knowledge data
- Deprecate per-project databases completely
- Add project information to entities, observations, and relations
- Simplify project switching and management
- Enable better multi-project support for the Pro app
- Prepare for cloud/GoHighLevel integration

## Architecture Changes

We're moving from:
```
~/.basic-memory/config.json (project list)
~/basic-memory/[project-name]/.basic-memory/memory.db (one DB per project)
```

To:
```
~/.basic-memory/config.json (project list)  <- same
~/.basic-memory/memory.db (app-level DB with project/entity/observation/search_index tables)
~/basic-memory/[project-name]/.basic-memory/memory.db (project DBs deprecated) <- we are removing these
```

## Implementation Tasks

### 1. Configuration Changes

- [x] Update config.py to use a single app database for all projects
- [x] Add functions to get app database path for all operations
- [x] Keep JSON-based config.json for project listing/paths
- [x] Update project configuration loading to use app DB for all operations


### 3. Project Model Implementation

- [x] Create Project SQLAlchemy model in models/project.py
- [x] Define attributes: id, name, path, config, etc.
- [x] Add proper indexes and constraints
- [x] Add project_id foreign key to Entity, Observation, and Relation models
- [ ] Create migration script for updating schema with project relations
- [ ] Implement app DB initialization with project table

### 4. Repository Layer Updates

- [x] Create ProjectRepository for CRUD operations on Project model
- [x] Update base Repository class to filter queries by project_id
- [x] Update existing repositories to use project context automatically
- [x] Implement query scoping to specific projects
- [x] Add functions for project context management

### 5. Search Functionality Updates

- [x] Update search_index table to include project_id
- [x] Modify search queries to filter by project_id
- [x] Update FTS (Full Text Search) to be project-aware
- [x] Add appropriate indices for efficient project-scoped searches
- [x] Update search repository for project context

### 6. Service Layer Updates

- [ ] Update ProjectService to manage projects in the database
- [ ] Add methods for project creation, deletion, updating
- [ ] Modify existing services to use project context
- [ ] Update initialization service for app DB setup
- [ ] Implement project switching logic

### 7. Sync Service Updates

- [ ] Modify background sync service to handle project context
- [ ] Update file watching to support multiple project directories
- [ ] Add project context to file sync events
- [ ] Update file path resolution to respect project boundaries
- [ ] Handle file change detection with project awareness

### 8. API Layer Updates

- [ ] Update API endpoints to include project context
- [ ] Create new endpoints for project management
- [ ] Modify dependency injection to include project context
- [ ] Add request/response models for project operations
- [ ] Implement middleware for project context handling
- [ ] Update error handling to include project information

### 9. MCP Tools Updates

- [ ] Update MCP tools to include project context
- [ ] Add project selection capabilities to MCP server
- [ ] Update context building to respect project boundaries
- [ ] Update file operations to handle project paths correctly
- [ ] Add project-aware helper functions for MCP tools

### 10. CLI Updates

- [ ] Update CLI commands to work with app DB
- [ ] Add or update project management commands
- [ ] Implement project switching via app DB
- [ ] Ensure CLI help text reflects new project structure
- [ ] Add migration commands for existing projects

### 11. Performance Optimizations

- [ ] Add proper indices for efficient project filtering
- [ ] Optimize queries for multi-project scenarios
- [ ] Add query caching if needed
- [ ] Monitor and optimize performance bottlenecks

### 12. Testing Updates

- [ ] Update test fixtures to support project context
- [ ] Add multi-project testing scenarios
- [ ] Create tests for migration processes
- [ ] Test performance with larger multi-project datasets

### 13 Migrations

- [ ] project table
- [ ] search project_id index
- [ ] project import/sync - during initialization

## Database Schema Changes

### New Project Table
```sql
CREATE TABLE project (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    path TEXT NOT NULL,
    config JSON,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Modified Entity Table
```sql
ALTER TABLE entity ADD COLUMN project_id INTEGER REFERENCES project(id);
CREATE INDEX ix_entity_project_id ON entity(project_id);
```

### Modified Observation Table
```sql
-- No direct changes needed as observations are linked to entities which have project_id
CREATE INDEX ix_observation_entity_project_id ON observation(entity_id, project_id);
```

### Modified Relation Table
```sql
-- No direct changes needed as relations are linked to entities which have project_id
CREATE INDEX ix_relation_from_project_id ON relation(from_id, project_id);
CREATE INDEX ix_relation_to_project_id ON relation(to_id, project_id);
```

## Migration Path

For existing projects, we'll:
1. Create the project table in the app database
2. For each project in config.json:
   a. Register the project in the project table
   b. Import all entities, observations, and relations from the project's DB
   c. Set the project_id on all imported records
3. Validate that all data has been migrated correctly
4. Keep config.json but use the database as the source of truth

## Testing

- Test project creation, switching, deletion
- Test knowledge operations (entity, observation, relation) with project context
- Verify existing projects can be migrated successfully
- Test multi-project operations
- Test error cases (missing project, etc.)
- Test CLI commands with multiple projects