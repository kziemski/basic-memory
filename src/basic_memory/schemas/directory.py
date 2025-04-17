"""Schemas for directory tree operations."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field


class DirectoryItem(BaseModel):
    """Directory or file node in the directory tree."""

    index: str
    canMove: bool
    isFolder: bool
    children: List[str]
    data: str
    canRename: bool


class DirectoryTree(BaseModel):
    """Old format for directory tree (RCT v1 compatible)."""
    items: Dict[str, DirectoryItem]


class DirectoryNode(BaseModel):
    """Directory node in file system."""
    
    name: str
    path: str
    type: Literal["directory", "file"]
    has_children: bool = False
    title: Optional[str] = None
    permalink: Optional[str] = None
    entity_id: Optional[int] = None
    entity_type: Optional[str] = None
    content_type: Optional[str] = None
    updated_at: Optional[datetime] = None
    parent_path: Optional[str] = None
    
    
class DirectoryTreeResponse(BaseModel):
    """Modern directory tree response for API."""
    
    base_path: str
    items: List[DirectoryNode]