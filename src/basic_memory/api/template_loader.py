"""Template loading and rendering utilities for the Basic Memory API.

This module handles the loading and rendering of Handlebars templates from the
templates directory, providing a consistent interface for all prompt-related
formatting needs.
"""

import os
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import json
import datetime

import pybars
from loguru import logger

# Get the base path of the templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


# Custom helpers for Handlebars
def _date_helper(context, options, timestamp, format_str="%Y-%m-%d %H:%M"):
    """Format a date using the given format string."""
    if hasattr(timestamp, "strftime"):
        return timestamp.strftime(format_str)
    elif isinstance(timestamp, str):
        try:
            dt = datetime.datetime.fromisoformat(timestamp)
            return dt.strftime(format_str)
        except ValueError:
            return timestamp
    return str(timestamp)


def _default_helper(context, value, default_value):
    """Return a default value if the given value is None or empty."""
    if value is None or value == "":
        return default_value
    return value


def _capitalize_helper(context, options, text):
    """Capitalize the first letter of a string."""
    if not text or not isinstance(text, str):
        return ""
    return text.capitalize()


def _round_helper(context, options, value, decimal_places=2):
    """Round a number to the specified number of decimal places."""
    try:
        return round(float(value), int(decimal_places))
    except (ValueError, TypeError):
        return value


def _size_helper(context, options, value):
    """Return the size/length of a collection."""
    if value is None:
        return 0
    if isinstance(value, (list, tuple, dict, str)):
        return len(value)
    return 0


def _json_helper(context, options, value):
    """Convert a value to a JSON string."""
    return json.dumps(value)


def _math_helper(context, options, lhs, operator, rhs):
    """Perform basic math operations."""
    try:
        lhs = float(lhs)
        rhs = float(rhs)
        if operator == "+":
            return lhs + rhs
        elif operator == "-":
            return lhs - rhs
        elif operator == "*":
            return lhs * rhs
        elif operator == "/":
            return lhs / rhs
        else:
            return f"Unsupported operator: {operator}"
    except (ValueError, TypeError) as e:
        return f"Math error: {e}"


def _lt_helper(context, options, lhs, rhs):
    """Check if left hand side is less than right hand side."""
    try:
        return float(lhs) < float(rhs)
    except (ValueError, TypeError):
        # Fall back to string comparison for non-numeric values
        return str(lhs) < str(rhs)


class TemplateLoader:
    """Loader for Handlebars templates.
    
    This class is responsible for loading templates from disk and rendering
    them with the provided context data.
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        """Initialize the template loader.
        
        Args:
            template_dir: Optional custom template directory path
        """
        self.template_dir = Path(template_dir) if template_dir else TEMPLATES_DIR
        self.template_cache: Dict[str, Callable] = {}
        self.compiler = pybars.Compiler()
        
        # Set up standard helpers
        self.helpers = {
            "date": _date_helper,
            "default": _default_helper,
            "capitalize": _capitalize_helper,
            "round": _round_helper,
            "size": _size_helper,
            "json": _json_helper,
            "math": _math_helper,
            "lt": _lt_helper,
        }
        
        logger.debug(f"Initialized template loader with directory: {self.template_dir}")
    
    def get_template(self, template_path: str) -> Callable:
        """Get a template by path, using cache if available.
        
        Args:
            template_path: The path to the template, relative to the templates directory
            
        Returns:
            The compiled Handlebars template
            
        Raises:
            FileNotFoundError: If the template doesn't exist
        """
        if template_path in self.template_cache:
            return self.template_cache[template_path]
        
        # Convert from Liquid-style path to Handlebars extension
        if template_path.endswith(".liquid"):
            template_path = template_path.replace(".liquid", ".hbs")
        elif not template_path.endswith(".hbs"):
            template_path = f"{template_path}.hbs"
        
        full_path = self.template_dir / template_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"Template not found: {full_path}")
        
        with open(full_path, 'r') as f:
            template_str = f.read()
            
        template = self.compiler.compile(template_str)
        self.template_cache[template_path] = template
        
        logger.debug(f"Loaded template: {template_path}")
        return template
    
    async def render(self, template_path: str, context: Dict[str, Any]) -> str:
        """Render a template with the given context.
        
        Args:
            template_path: The path to the template, relative to the templates directory
            context: The context data to pass to the template
            
        Returns:
            The rendered template as a string
        """
        template = self.get_template(template_path)
        return template(context, helpers=self.helpers)
    
    def clear_cache(self) -> None:
        """Clear the template cache."""
        self.template_cache.clear()
        logger.debug("Template cache cleared")


# Global template loader instance
template_loader = TemplateLoader()