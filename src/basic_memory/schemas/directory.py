"""Schemas for directory tree operations."""

from datetime import datetime
from typing import List, Optional, Literal, Dict

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
    items: Dict[str, DirectoryItem]