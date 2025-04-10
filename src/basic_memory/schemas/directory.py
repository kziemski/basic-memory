"""Schemas for directory tree operations."""

from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class DirectoryNodeSchema(BaseModel):
    """Directory or file node in the directory tree."""
    
    name: str = Field(description="Name of the file or directory")
    path: str = Field(description="Full path of the file or directory")
    type: Literal["directory", "file"] = Field(description="Type of node")
    has_children: bool = Field(description="Whether the node can have children")
    title: str = Field(description="Display title for the node")
    permalink: Optional[str] = Field(None, description="Permalink for file node")
    entity_id: Optional[int] = Field(None, description="Entity ID for file node")
    entity_type: Optional[str] = Field(None, description="Entity type for file node")
    content_type: Optional[str] = Field(None, description="Content MIME type for file node")
    updated_at: Optional[str] = Field(None, description="Last updated timestamp for file node")


class DirectoryTreeSchema(BaseModel):
    """Response schema for directory tree operations."""
    
    items: List[DirectoryNodeSchema] = Field(description="List of directory nodes")
    path: str = Field(description="Current path being displayed")
    depth: int = Field(description="Depth level of nodes being displayed")
    parent_path: Optional[str] = Field(None, description="Path of parent directory, if any")
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "name": "docs",
                        "path": "/docs",
                        "type": "directory",
                        "has_children": True,
                        "title": "docs",
                        "permalink": None,
                        "entity_id": None,
                        "entity_type": None,
                        "content_type": None,
                        "updated_at": None
                    },
                    {
                        "name": "README.md",
                        "path": "/README.md",
                        "type": "file",
                        "has_children": False,
                        "title": "Basic Memory",
                        "permalink": "readme",
                        "entity_id": 1,
                        "entity_type": "note",
                        "content_type": "text/markdown",
                        "updated_at": "2023-01-01T12:00:00"
                    }
                ],
                "path": "/",
                "depth": 1,
                "parent_path": None
            }
        }