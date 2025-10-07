"""
Data layer for Tobbes v2.

This module provides database access through the DatabaseInterface abstraction.
Use create_database() factory function to get a database instance.
"""

from pathlib import Path
from typing import Literal, Union

from .interface import DatabaseInterface
from .sqlite_db import SQLiteDatabase


def create_database(
    backend: Literal["sqlite"] = "sqlite",
    path: Union[str, Path] = "./tobbes_data.db",
) -> DatabaseInterface:
    """
    Factory function to create database instance.

    Args:
        backend: Database backend to use (currently only "sqlite")
        path: Path to database file (for SQLite)

    Returns:
        DatabaseInterface implementation

    Example:
        >>> db = create_database("sqlite", "./my_project.db")
        >>> projects = db.list_projects()
    """
    if backend == "sqlite":
        return SQLiteDatabase(path)
    else:
        raise ValueError(f"Unknown database backend: {backend}")


__all__ = [
    "DatabaseInterface",
    "SQLiteDatabase",
    "create_database",
]
